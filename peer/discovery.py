"""
Système de découverte locale via UDP pour le mode dégradé (sans tracker).
"""

import socket
import json
import logging
from threading import Thread, Event
from typing import List, Callable, Optional
from datetime import datetime, timedelta

from shared.models import UDPAnnouncement, PeerInfo, FileInfo
from shared.network import create_udp_socket, get_local_ip, get_broadcast_address

logger = logging.getLogger(__name__)


class UDPDiscovery:
    """
    Gère la découverte de peers via broadcast/multicast UDP.
    """
    
    def __init__(self, config: dict, peer_id: str, peer_name: str, peer_port: int):
        """
        Initialise le système de découverte.
        
        Args:
            config: Configuration de l'application
            peer_id: ID du peer local
            peer_name: Nom du peer local
            peer_port: Port du serveur peer
        """
        self.config = config
        self.discovery_config = config['discovery']
        
        self.peer_id = peer_id
        self.peer_name = peer_name
        self.peer_port = peer_port
        self.local_ip = get_local_ip()
        
        self.broadcast_port = self.discovery_config['broadcast_port']
        self.broadcast_interval = self.discovery_config['broadcast_interval']
        self.peer_timeout = self.discovery_config['peer_timeout']
        
        # Peers découverts {peer_id: (PeerInfo, last_seen)}
        self.discovered_peers: dict = {}
        
        # Sockets
        self._send_socket: Optional[socket.socket] = None
        self._recv_socket: Optional[socket.socket] = None
        
        # Threads
        self._announce_thread: Optional[Thread] = None
        self._listen_thread: Optional[Thread] = None
        self._cleanup_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Callbacks
        self.on_peer_discovered: Optional[Callable] = None
        self.on_peer_lost: Optional[Callable] = None
        
        logger.info(f"Découverte UDP initialisée sur port {self.broadcast_port}")
    
    def start(self):
        """
        Démarre le système de découverte.
        """
        if not self.discovery_config['enabled']:
            logger.info("Découverte UDP désactivée dans la configuration")
            return
        
        try:
            # Créer les sockets
            self._send_socket = create_udp_socket(broadcast=True)
            self._recv_socket = create_udp_socket(
                bind_address=('', self.broadcast_port),
                broadcast=True
            )
            
            # Démarrer les threads
            self._stop_event.clear()
            
            self._announce_thread = Thread(target=self._announce_loop, daemon=True)
            self._announce_thread.start()
            
            self._listen_thread = Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()
            
            self._cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            
            logger.info("Découverte UDP démarrée")
            
        except Exception as e:
            logger.error(f"Erreur démarrage découverte UDP : {e}")
            self.stop()
    
    def stop(self):
        """
        Arrête le système de découverte.
        """
        logger.info("Arrêt de la découverte UDP...")
        
        # Envoyer un message GOODBYE
        self._send_goodbye()
        
        # Arrêter les threads
        self._stop_event.set()
        
        if self._announce_thread:
            self._announce_thread.join(timeout=2)
        if self._listen_thread:
            self._listen_thread.join(timeout=2)
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)
        
        # Fermer les sockets
        if self._send_socket:
            self._send_socket.close()
        if self._recv_socket:
            self._recv_socket.close()
        
        logger.info("Découverte UDP arrêtée")
    
    def _announce_loop(self):
        """
        Boucle d'annonce périodique.
        """
        while not self._stop_event.is_set():
            try:
                self._send_announcement()
            except Exception as e:
                logger.error(f"Erreur lors de l'annonce : {e}")
            
            self._stop_event.wait(self.broadcast_interval)
    
    def _listen_loop(self):
        """
        Boucle d'écoute des annonces.
        """
        self._recv_socket.settimeout(1.0)
        
        while not self._stop_event.is_set():
            try:
                data, addr = self._recv_socket.recvfrom(65535)
                self._handle_announcement(data, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error(f"Erreur lors de l'écoute : {e}")
    
    def _cleanup_loop(self):
        """
        Boucle de nettoyage des peers inactifs.
        """
        while not self._stop_event.is_set():
            try:
                self._cleanup_inactive_peers()
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage : {e}")
            
            self._stop_event.wait(30)  # Toutes les 30 secondes
    
    def _send_announcement(self, announcement_type: str = 'ANNOUNCE'):
        """
        Envoie une annonce UDP.
        
        Args:
            announcement_type: Type d'annonce (ANNOUNCE, GOODBYE)
        """
        try:
            announcement = UDPAnnouncement(
                type=announcement_type,
                peer_id=self.peer_id,
                peer_name=self.peer_name,
                ip=self.local_ip,
                port=self.peer_port,
                files=[],  # Les fichiers sont demandés séparément
                timestamp=datetime.now().timestamp()
            )
            
            message = announcement.to_json().encode('utf-8')
            
            # Broadcast
            broadcast_addr = get_broadcast_address(self.local_ip)
            self._send_socket.sendto(message, (broadcast_addr, self.broadcast_port))
            
            logger.debug(f"Annonce {announcement_type} envoyée")
            
        except Exception as e:
            logger.error(f"Erreur envoi annonce : {e}")
    
    def _send_goodbye(self):
        """
        Envoie un message de départ.
        """
        self._send_announcement('GOODBYE')
    
    def _handle_announcement(self, data: bytes, addr: tuple):
        """
        Traite une annonce reçue.
        
        Args:
            data: Données reçues
            addr: Adresse de l'émetteur
        """
        try:
            # Décoder le message
            message = json.loads(data.decode('utf-8'))
            announcement = UDPAnnouncement.from_dict(message)
            
            # Ignorer ses propres messages
            if announcement.peer_id == self.peer_id:
                return
            
            logger.debug(f"Annonce reçue de {announcement.peer_name} ({announcement.type})")
            
            # Traiter selon le type
            if announcement.type == 'ANNOUNCE':
                self._handle_peer_announce(announcement)
            elif announcement.type == 'GOODBYE':
                self._handle_peer_goodbye(announcement)
            elif announcement.type == 'QUERY':
                self._handle_query(announcement)
            elif announcement.type == 'RESPONSE':
                self._handle_response(announcement)
                
        except json.JSONDecodeError:
            logger.warning(f"Message UDP invalide reçu de {addr}")
        except Exception as e:
            logger.error(f"Erreur traitement annonce : {e}")
    
    def _handle_peer_announce(self, announcement: UDPAnnouncement):
        """
        Traite une annonce de peer.
        
        Args:
            announcement: Annonce reçue
        """
        peer_info = PeerInfo(
            id=announcement.peer_id,
            name=announcement.peer_name,
            ip_address=announcement.ip,
            port=announcement.port,
            status='online'
        )
        
        # Vérifier si c'est un nouveau peer
        is_new = announcement.peer_id not in self.discovered_peers
        
        # Mettre à jour les peers découverts
        self.discovered_peers[announcement.peer_id] = (
            peer_info,
            datetime.now()
        )
        
        # Notifier si nouveau
        if is_new and self.on_peer_discovered:
            try:
                self.on_peer_discovered(peer_info)
            except Exception as e:
                logger.error(f"Erreur callback on_peer_discovered : {e}")
        
        logger.info(f"Peer {'découvert' if is_new else 'mis à jour'} : "
                   f"{peer_info.name} ({peer_info.ip_address}:{peer_info.port})")
    
    def _handle_peer_goodbye(self, announcement: UDPAnnouncement):
        """
        Traite un message de départ d'un peer.
        
        Args:
            announcement: Annonce reçue
        """
        if announcement.peer_id in self.discovered_peers:
            peer_info, _ = self.discovered_peers.pop(announcement.peer_id)
            
            # Notifier
            if self.on_peer_lost:
                try:
                    self.on_peer_lost(peer_info)
                except Exception as e:
                    logger.error(f"Erreur callback on_peer_lost : {e}")
            
            logger.info(f"Peer parti : {peer_info.name}")
    
    def _handle_query(self, announcement: UDPAnnouncement):
        """
        Traite une requête de recherche.
        
        Args:
            announcement: Requête reçue
        """
        # TODO: Implémenter la recherche locale et répondre
        logger.debug(f"Requête de recherche reçue de {announcement.peer_name}")
    
    def _handle_response(self, announcement: UDPAnnouncement):
        """
        Traite une réponse à une recherche.
        
        Args:
            announcement: Réponse reçue
        """
        # TODO: Traiter les résultats de recherche
        logger.debug(f"Réponse de recherche reçue de {announcement.peer_name}")
    
    def _cleanup_inactive_peers(self):
        """
        Nettoie les peers inactifs (timeout dépassé).
        """
        cutoff = datetime.now() - timedelta(seconds=self.peer_timeout)
        
        inactive_peers = []
        
        for peer_id, (peer_info, last_seen) in list(self.discovered_peers.items()):
            if last_seen < cutoff:
                inactive_peers.append((peer_id, peer_info))
        
        # Supprimer les peers inactifs
        for peer_id, peer_info in inactive_peers:
            del self.discovered_peers[peer_id]
            
            # Notifier
            if self.on_peer_lost:
                try:
                    self.on_peer_lost(peer_info)
                except Exception as e:
                    logger.error(f"Erreur callback on_peer_lost : {e}")
            
            logger.info(f"Peer inactif supprimé : {peer_info.name}")
    
    def get_discovered_peers(self) -> List[PeerInfo]:
        """
        Retourne la liste des peers découverts.
        
        Returns:
            Liste de PeerInfo
        """
        return [peer_info for peer_info, _ in self.discovered_peers.values()]
    
    def is_peer_online(self, peer_id: str) -> bool:
        """
        Vérifie si un peer est en ligne.
        
        Args:
            peer_id: ID du peer
            
        Returns:
            True si en ligne, False sinon
        """
        return peer_id in self.discovered_peers
    
    def get_statistics(self) -> dict:
        """
        Retourne des statistiques sur la découverte.
        
        Returns:
            Dictionnaire de statistiques
        """
        return {
            'enabled': self.discovery_config['enabled'],
            'discovered_peers': len(self.discovered_peers),
            'broadcast_port': self.broadcast_port,
            'local_ip': self.local_ip
        }