"""
Application principale du peer P2P.
Orchestre tous les composants : scanner, serveur, client, découverte, etc.
"""

import logging
import signal
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import requests
from apscheduler.schedulers.background import BackgroundScheduler

from peer import create_app, set_peer_instance
from peer.file_scanner import FileScanner
from peer.chunk_manager import ChunkManager
from peer.cache_manager import CacheManager
from peer.discovery import UDPDiscovery
from peer.peer_server import PeerServer
from peer.peer_client import PeerClient
from peer.routes import peer_bp, init_routes
from peer.distributed_chunking import DistributedChunkManager

from shared.models import PeerInfo, FileInfo, DownloadJob, TrackerStatus
from shared.network import get_local_ip, find_free_port
from shared.crypto import generate_peer_id
from shared.utils import get_hostname, get_or_create_peer_id
from shared.constants import PEER_STATUS_ONLINE

logger = logging.getLogger(__name__)


class PeerApplication:
    """
    Application peer complète orchestrant tous les composants.
    """
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialise l'application peer.
        
        Args:
            config_path: Chemin du fichier de configuration
        """
        # Créer l'application Flask
        self.flask_app = create_app(config_path)
        self.config = self.flask_app.config['APP_CONFIG']
        
        # Informations du peer - ID persistant basé sur la machine
        self.peer_id = get_or_create_peer_id()  # ID unique et persistant
        self.peer_name = get_hostname()
        self.local_ip = get_local_ip()
        
        # Trouver un port disponible
        port_range = self.config['peer']['port_range']
        self.peer_port = find_free_port(port_range['start'], port_range['end'])
        
        if not self.peer_port:
            raise RuntimeError("Aucun port disponible dans la plage configurée")
        
        logger.info(f"Peer initialisé : {self.peer_name} ({self.peer_id[:8]}...)")
        logger.info(f"Adresse locale : {self.local_ip}:{self.peer_port}")
        
        # Composants
        self.chunk_manager = ChunkManager(self.config)
        self.cache_manager = CacheManager(self.config['peer']['cache_database'])
        
        self.file_scanner = FileScanner(
            self.config['peer']['shared_folder'],
            self.config
        )
        
        self.udp_discovery = UDPDiscovery(
            self.config,
            self.peer_id,
            self.peer_name,
            self.peer_port
        )
        
        self.peer_server = PeerServer(
            '0.0.0.0',
            self.peer_port,
            self.file_scanner,
            self.chunk_manager,
            self.config
        )
        
        self.peer_client = PeerClient(
            self.chunk_manager,
            self.config
        )
        
        # Gestionnaire de fragmentation distribuée (initialisé après les autres composants)
        self.distributed_chunk_manager = None  # Sera initialisé après le démarrage du cache
        
        # État de connexion au tracker
        self.tracker_url: Optional[str] = None
        self.tracker_connected = False
        self.tracker_status = TrackerStatus(is_connected=False)
        
        # Scheduler pour tâches périodiques
        self.scheduler = BackgroundScheduler()
        
        # Enregistrer les routes Flask
        init_routes(self)
        self.flask_app.register_blueprint(peer_bp)
        
        # Injecter le peer_id dans le serveur
        self.peer_server.peer_id = self.peer_id
        
        # Définir l'instance globale
        set_peer_instance(self)
        
        # Configuration des callbacks
        self._setup_callbacks()
        
        logger.info("✅ Application peer initialisée")
    
    def _setup_callbacks(self):
        """
        Configure les callbacks entre les composants.
        """
        # Scanner -> Tracker
        self.file_scanner.on_file_added = self._on_file_added
        self.file_scanner.on_file_removed = self._on_file_removed
        
        # Découverte UDP -> Cache
        self.udp_discovery.on_peer_discovered = self._on_peer_discovered
        self.udp_discovery.on_peer_lost = self._on_peer_lost
        
        # Client downloads
        self.peer_client.on_download_completed = self._on_download_completed
        self.peer_client.on_download_failed = self._on_download_failed
    
    def start(self):
        """
        Démarre tous les composants du peer.
        """
        try:
            logger.info("🚀 Démarrage du peer...")
            
            # 1. Scanner initial des fichiers
            logger.info("📁 Scan des fichiers partagés...")
            self.file_scanner.scan_files()
            
            # 2. Initialiser le gestionnaire de fragmentation distribuée (nécessite cache_manager)
            logger.info("🔨 Initialisation du gestionnaire de fragmentation...")
            self.distributed_chunk_manager = DistributedChunkManager(
                config=self.config,
                chunk_manager=self.chunk_manager,
                peer_client=self.peer_client,
                cache_manager=self.cache_manager
            )
            
            # 3. Démarrer le serveur peer
            logger.info("🌐 Démarrage du serveur peer...")
            self.peer_server.start()
            
            # 4. Démarrer le client de téléchargement
            logger.info("⬇️ Démarrage du client de téléchargement...")
            self.peer_client.start()
            
            # 5. Connexion au tracker
            logger.info("📡 Connexion au tracker...")
            tracker_config = self.config['tracker']
            # Si le tracker écoute sur 0.0.0.0, le client doit se connecter à localhost
            tracker_host = tracker_config['host'] if tracker_config['host'] != '0.0.0.0' else 'localhost'
            self.tracker_url = f"http://{tracker_host}:{tracker_config['port']}"
            connected = self.connect_to_tracker()
            if connected:
                logger.info(f"✅ Enregistrement initial réussi auprès du tracker")
            else:
                logger.warning(f"⚠️ Échec de l'enregistrement initial - mode dégradé activé")
            
            # 6. Démarrer la découverte UDP
            logger.info("📻 Démarrage de la découverte UDP...")
            self.udp_discovery.start()
            
            # 7. Démarrer le scanner automatique
            logger.info("🔄 Démarrage du scan automatique...")
            self.file_scanner.start_auto_scan()
            
            # 8. Démarrer les tâches périodiques
            logger.info("⏰ Démarrage des tâches périodiques...")
            self._start_scheduled_tasks()
            
            logger.info("=" * 60)
            logger.info(f"✅ Peer démarré avec succès !")
            logger.info(f"   Serveur peer : http://{self.local_ip}:{self.peer_port}")
            logger.info(f"   Fichiers partagés : {len(self.file_scanner.get_files())}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage : {e}")
            self.stop()
            raise
    
    def stop(self):
        """
        Arrête tous les composants du peer.
        """
        logger.info("🛑 Arrêt du peer...")
        
        # Déconnexion du tracker
        if self.tracker_connected:
            self.disconnect_from_tracker()
        
        # Arrêter les composants
        self.file_scanner.stop_auto_scan()
        self.udp_discovery.stop()
        self.peer_client.stop()
        self.peer_server.stop()
        
        # Arrêter le scheduler
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        logger.info("✅ Peer arrêté")
    
    def connect_to_tracker(self) -> bool:
        """
        Se connecte au tracker central.
        
        Returns:
            True si succès, False sinon
        """
        try:
            logger.info(f"🔗 Tentative de connexion à {self.tracker_url}/api/register")
            
            # S'enregistrer auprès du tracker
            peer_info = PeerInfo(
                id=self.peer_id,
                name=self.peer_name,
                ip_address=self.local_ip,
                port=self.peer_port,
                status='online'
            )
            
            logger.info(f"📤 Envoi des données : {peer_info.to_dict()}")
            
            response = requests.post(
                f"{self.tracker_url}/api/register",
                json=peer_info.to_dict(),
                timeout=10
            )
            
            logger.info(f"📥 Réponse tracker : Status {response.status_code}, Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.tracker_connected = True
                    self.tracker_status.is_connected = True
                    self.tracker_status.last_heartbeat = datetime.now().timestamp()
                    
                    logger.info(f"✅ Connecté au tracker : {self.tracker_url}")
                    
                    # Synchroniser les fichiers
                    self.sync_files_with_tracker()
                    
                    return True
            
            logger.warning(f"⚠️ Échec connexion tracker : {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion tracker : {e}")
            self.tracker_connected = False
            self.tracker_status.is_connected = False
            self.tracker_status.error_message = str(e)
            return False
    
    def disconnect_from_tracker(self):
        """
        Se déconnecte du tracker.
        """
        try:
            if self.tracker_connected:
                requests.post(
                    f"{self.tracker_url}/api/unregister",
                    json={'peer_id': self.peer_id},
                    timeout=5
                )
                logger.info("Déconnecté du tracker")
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion : {e}")
        finally:
            self.tracker_connected = False
            self.tracker_status.is_connected = False
    
    def sync_files_with_tracker(self):
        """
        Synchronise la liste des fichiers avec le tracker.
        """
        if not self.tracker_connected:
            return
        
        try:
            files = self.file_scanner.get_files()
            
            # Préparer les fichiers avec informations de chunking
            files_data = []
            for file_info in files:
                if file_info.is_chunked and not file_info.chunks_hashes:
                    # Calculer les hashes de chunks si nécessaire
                    filepath = self.file_scanner.get_file_path(file_info)
                    file_info = self.chunk_manager.prepare_file_info_for_chunking(
                        file_info, filepath
                    )
                
                file_info.owner_id = self.peer_id
                files_data.append(file_info.to_dict())
            
            # Envoyer au tracker
            response = requests.post(
                f"{self.tracker_url}/api/announce_files",
                json={'peer_id': self.peer_id, 'files': files_data},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ {len(files)} fichiers synchronisés avec le tracker")
            
        except Exception as e:
            logger.error(f"Erreur synchronisation fichiers : {e}")
    
    def send_heartbeat(self):
        """
        Envoie un heartbeat au tracker.
        """
        if not self.tracker_connected:
            return
        
        try:
            response = requests.post(
                f"{self.tracker_url}/api/heartbeat",
                json={'peer_id': self.peer_id},
                timeout=5
            )
            
            if response.status_code == 200:
                self.tracker_status.last_heartbeat = datetime.now().timestamp()
                logger.debug("Heartbeat envoyé au tracker")
            else:
                logger.warning(f"Heartbeat échoué : {response.status_code}")
                self.tracker_connected = False
                self.tracker_status.is_connected = False
        
        except Exception as e:
            logger.error(f"Erreur heartbeat : {e}")
            self.tracker_connected = False
            self.tracker_status.is_connected = False
    
    def try_reconnect_tracker(self):
        """
        Tente de se reconnecter au tracker si la connexion est perdue.
        """
        if not self.tracker_connected:
            try:
                logger.info("Tentative de reconnexion au tracker...")
                success = self.connect_to_tracker()
                if success:
                    logger.info("✅ Reconnexion au tracker réussie !")
                    # Resynchroniser les fichiers
                    self.sync_files_with_tracker()
            except Exception as e:
                logger.warning(f"Échec reconnexion : {e}")
    
    def search_files(self, query: str, limit: int = 50, 
                    only_online: bool = True) -> List[FileInfo]:
        """
        Recherche des fichiers dans le réseau.
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            only_online: Ne retourner que les fichiers de peers en ligne
            
        Returns:
            Liste de FileInfo
        """
        results = []
        
        # Rechercher dans le tracker si connecté
        if self.tracker_connected:
            try:
                response = requests.get(
                    f"{self.tracker_url}/api/search",
                    params={'q': query, 'limit': limit},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        from shared.models import PeerInfo
                        results = []
                        # Traiter chaque fichier et stocker dans le cache
                        for file_data in data['files']:
                            # FileInfo.from_dict() va automatiquement filtrer les champs inconnus
                            file_info = FileInfo.from_dict(file_data)
                            results.append(file_info)
                            self.cache_manager.add_file(file_info)
                            
                            # Stocker aussi les infos du peer propriétaire
                            if file_data.get('owner_id') and file_data.get('owner_ip'):
                                peer_info = PeerInfo(
                                    id=file_data['owner_id'],
                                    name=file_data.get('owner_name', 'Unknown'),
                                    ip_address=file_data['owner_ip'],
                                    port=file_data.get('owner_port', 0),
                                    status=file_data.get('owner_status', PEER_STATUS_ONLINE)
                                )
                                self.cache_manager.add_peer(peer_info)
                
            except Exception as e:
                logger.error(f"Erreur recherche tracker : {e}", exc_info=True)
        
        # Compléter avec le cache local
        cached_results = self.cache_manager.search_files(query, limit)
        
        # Fusionner les résultats (éviter doublons)
        seen_hashes = {f.hash for f in results}
        for f in cached_results:
            if f.hash not in seen_hashes:
                results.append(f)
                seen_hashes.add(f.hash)
        
        return results[:limit]
    
    def download_file(self, file_id: str, peer_id: str) -> Optional[DownloadJob]:
        """
        Télécharge un fichier depuis un peer.
        
        Args:
            file_id: ID du fichier
            peer_id: ID du peer source
            
        Returns:
            DownloadJob créé ou None
        """
        try:
            # Récupérer les infos du fichier depuis le cache
            file_info = self.cache_manager.get_file(file_id)
            
            if not file_info:
                logger.error(f"Fichier {file_id} introuvable dans le cache. Assurez-vous de rechercher le fichier avant de le télécharger.")
                return None
            
            # Récupérer les infos du peer
            peer_info = self.cache_manager.get_peer(peer_id)
            
            if not peer_info:
                logger.error(f"Peer {peer_id} introuvable")
                return None
            
            logger.info(f"📍 Peer trouvé dans le cache : {peer_info.name}")
            logger.info(f"📍 IP: {peer_info.ip_address}, Port: {peer_info.port}")
            logger.info(f"📍 Peer dict complet: {peer_info.to_dict()}")
            
            # Créer le chemin de destination
            download_folder = Path(self.config['peer']['download_folder'])
            download_folder.mkdir(parents=True, exist_ok=True)
            
            destination = str(download_folder / file_info.name)
            
            # Démarrer le téléchargement
            job = self.peer_client.add_download(file_info, peer_info, destination)
            
            logger.info(f"Téléchargement démarré : {file_info.name}")
            
            return job
            
        except Exception as e:
            logger.error(f"Erreur démarrage téléchargement : {e}")
            return None
    
    def _start_scheduled_tasks(self):
        """
        Démarre les tâches périodiques.
        """
        # Heartbeat au tracker
        heartbeat_interval = self.config['tracker']['heartbeat']['interval']
        self.scheduler.add_job(
            self.send_heartbeat,
            'interval',
            seconds=heartbeat_interval,
            id='heartbeat'
        )
        
        # Tentative de reconnexion au tracker si déconnecté
        retry_interval = self.config['peer']['sync'].get('retry_connection', 30)
        self.scheduler.add_job(
            self.try_reconnect_tracker,
            'interval',
            seconds=retry_interval,
            id='tracker_reconnect'
        )
        
        # Nettoyage du cache
        self.scheduler.add_job(
            self.cache_manager.cleanup_old_entries,
            'interval',
            hours=1,
            id='cache_cleanup'
        )
        
        # Synchronisation des fichiers
        sync_interval = self.config['peer']['sync']['interval']
        self.scheduler.add_job(
            self.sync_files_with_tracker,
            'interval',
            seconds=sync_interval,
            id='file_sync'
        )
        
        self.scheduler.start()
        logger.info("Tâches périodiques démarrées")
    
    # Callbacks
    
    def _on_file_added(self, file_info: FileInfo):
        """Callback : fichier ajouté."""
        logger.info(f"Fichier ajouté : {file_info.name}")
        if self.tracker_connected:
            self.sync_files_with_tracker()
    
    def _on_file_removed(self, file_info: FileInfo):
        """Callback : fichier supprimé."""
        logger.info(f"Fichier supprimé : {file_info.name}")
        if self.tracker_connected:
            self.sync_files_with_tracker()
    
    def _on_peer_discovered(self, peer_info: PeerInfo):
        """Callback : peer découvert via UDP."""
        logger.info(f"Peer découvert : {peer_info.name}")
        self.cache_manager.add_peer(peer_info, 'udp')
    
    def _on_peer_lost(self, peer_info: PeerInfo):
        """Callback : peer perdu."""
        logger.info(f"Peer perdu : {peer_info.name}")
    
    def _on_download_completed(self, job: DownloadJob):
        """Callback : téléchargement terminé."""
        logger.info(f"✅ Téléchargement terminé : {job.file_info.name}")
    
    def _on_download_failed(self, job: DownloadJob):
        """Callback : téléchargement échoué."""
        logger.error(f"❌ Téléchargement échoué : {job.file_info.name} - {job.error_message}")
    
    # Utilitaires
    
    def get_statistics(self) -> dict:
        """
        Retourne les statistiques du peer.
        
        Returns:
            Dictionnaire de statistiques
        """
        return {
            'peer': {
                'id': self.peer_id,
                'name': self.peer_name,
                'ip': self.local_ip,
                'port': self.peer_port
            },
            'files': self.file_scanner.get_statistics(),
            'downloads': self.peer_client.get_statistics(),
            'cache': self.cache_manager.get_statistics(),
            'discovery': self.udp_discovery.get_statistics(),
            'tracker': self.tracker_status.to_dict()
        }
    
    def get_tracker_status(self) -> TrackerStatus:
        """Retourne le statut de connexion au tracker."""
        return self.tracker_status


def main():
    """
    Point d'entrée principal de l'application peer.
    """
    # Créer l'application
    peer_app = PeerApplication()
    
    # Gérer les signaux d'arrêt
    def signal_handler(sig, frame):
        logger.info("\n⚠️ Signal d'arrêt reçu")
        peer_app.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Démarrer le peer
        peer_app.start()
        
        # Démarrer l'interface web Flask sur un port différent
        # Le peer_server utilise peer_port (5001-5100), donc on utilise 8000+
        web_port = 8001
        
        logger.info(f"Démarrage de l'interface web sur le port {web_port}...")
        logger.info(f"Interface web du peer : http://localhost:{web_port}")
        
        peer_app.flask_app.run(
            host='0.0.0.0',
            port=web_port,
            debug=False,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interruption clavier")
    except Exception as e:
        logger.error(f"❌ Erreur fatale : {e}", exc_info=True)
    finally:
        peer_app.stop()


if __name__ == '__main__':
    main()