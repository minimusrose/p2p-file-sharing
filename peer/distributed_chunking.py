"""
Gestionnaire de fragmentation distribuée pour fichiers volumineux.
Distribue les chunks de fichiers ≥ 1GB sur plusieurs peers.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import requests

from shared.models import FileInfo, PeerInfo
from shared.crypto import calculate_chunk_hash

logger = logging.getLogger(__name__)


@dataclass
class ChunkDistribution:
    """Information sur la distribution d'un chunk"""
    file_id: str
    chunk_index: int
    peer_id: str
    chunk_hash: str
    stored_at: datetime
    is_available: bool = True


class DistributedChunkManager:
    """
    Gère la distribution des chunks de fichiers volumineux sur plusieurs peers.
    
    Responsabilités:
    - Détecter si un fichier doit être distribué (≥ 1GB)
    - Vérifier la disponibilité des peers
    - Distribuer les chunks équitablement
    - Envoyer/recevoir des chunks depuis d'autres peers
    - Gérer le mapping: chunk_index → peer_id
    """
    
    def __init__(self, config: dict, chunk_manager, peer_client, cache_manager):
        self.config = config
        self.chunk_manager = chunk_manager
        self.peer_client = peer_client
        self.cache_manager = cache_manager
        
        # Configuration
        self.min_file_size = config['chunking'].get('min_file_size_for_distribution', 1024 * 1024 * 1024)  # 1 GB
        self.min_peers_required = config['chunking'].get('min_peers_for_distribution', 2)
        self.distribution_strategy = config['chunking'].get('distribution_strategy', 'round_robin')
        self.chunk_size = config['chunking']['chunk_size']
        
        # Stockage local des chunks reçus d'autres peers
        self.distributed_chunks_dir = Path(config['peer']['download_folder']) / 'distributed_chunks'
        self.distributed_chunks_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DistributedChunkManager initialisé : min_size={self.min_file_size/1024/1024/1024}GB, min_peers={self.min_peers_required}")
    
    def should_distribute(self, file_size: int) -> bool:
        """
        Vérifie si un fichier doit être distribué sur plusieurs peers.
        
        Args:
            file_size: Taille du fichier en octets
            
        Returns:
            True si file_size ≥ min_file_size_for_distribution
        """
        return file_size >= self.min_file_size
    
    def get_available_peers(self) -> List[PeerInfo]:
        """
        Récupère la liste des peers disponibles pour la distribution.
        
        Returns:
            Liste de PeerInfo des peers connectés (excluant le peer local)
        """
        try:
            # Récupérer tous les peers depuis le cache
            all_peers = self.cache_manager.get_all_peers()
            
            # Filtrer: garder uniquement les peers en ligne et différents du peer local
            my_peer_id = self.config['peer']['id']
            available_peers = [
                peer for peer in all_peers 
                if peer.id != my_peer_id and peer.is_online
            ]
            
            logger.info(f"Peers disponibles pour distribution: {len(available_peers)}")
            return available_peers
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des peers: {e}")
            return []
    
    def can_distribute(self, file_size: int) -> Tuple[bool, str]:
        """
        Vérifie si un fichier peut être distribué (taille + peers disponibles).
        
        Args:
            file_size: Taille du fichier en octets
            
        Returns:
            (can_distribute: bool, message: str)
        """
        if not self.should_distribute(file_size):
            return True, "Fichier < 1GB, distribution non requise"
        
        available_peers = self.get_available_peers()
        
        if len(available_peers) < self.min_peers_required:
            msg = (
                f"Impossible d'uploader ce fichier ({file_size / 1024 / 1024 / 1024:.2f} GB). "
                f"Distribution requise mais seulement {len(available_peers)} peer(s) disponible(s). "
                f"Minimum requis : {self.min_peers_required} peers."
            )
            logger.warning(msg)
            return False, msg
        
        return True, f"{len(available_peers)} peer(s) disponible(s) pour distribution"
    
    def distribute_chunks(
        self, 
        file_info: FileInfo, 
        filepath: Path,
        chunks_hashes: List[str]
    ) -> Dict[int, str]:
        """
        Distribue les chunks d'un fichier sur les peers disponibles.
        
        Args:
            file_info: Métadonnées du fichier
            filepath: Chemin vers le fichier source
            chunks_hashes: Liste des hashes de tous les chunks
            
        Returns:
            Distribution map: {chunk_index: peer_id}
        """
        available_peers = self.get_available_peers()
        chunks_count = len(chunks_hashes)
        
        logger.info(f"Distribution de {chunks_count} chunks sur {len(available_peers)} peers")
        
        # Choisir la stratégie de distribution
        if self.distribution_strategy == 'balanced':
            distribution_map = self._distribute_balanced(chunks_count, available_peers)
        else:  # round_robin par défaut
            distribution_map = self._distribute_round_robin(chunks_count, available_peers)
        
        # Envoyer les chunks aux peers
        my_peer_id = self.config['peer']['id']
        success_count = 0
        failed_chunks = []
        
        for chunk_index, peer_id in distribution_map.items():
            # Garder les chunks locaux sans les envoyer
            if peer_id == my_peer_id:
                continue
            
            try:
                # Lire le chunk depuis le fichier source
                chunk_data = self.chunk_manager.read_chunk(filepath, chunk_index, file_info.size)
                chunk_hash = chunks_hashes[chunk_index]
                
                # Envoyer au peer distant
                success = self._send_chunk_to_peer(
                    peer_id=peer_id,
                    file_id=file_info.id,
                    chunk_index=chunk_index,
                    chunk_data=chunk_data,
                    chunk_hash=chunk_hash
                )
                
                if success:
                    success_count += 1
                else:
                    failed_chunks.append(chunk_index)
                    
            except Exception as e:
                logger.error(f"Erreur envoi chunk {chunk_index} vers peer {peer_id}: {e}")
                failed_chunks.append(chunk_index)
        
        logger.info(f"Distribution terminée: {success_count}/{chunks_count - distribution_map.get(my_peer_id, 0)} chunks envoyés")
        
        if failed_chunks:
            logger.warning(f"Chunks non envoyés: {failed_chunks}")
        
        return distribution_map
    
    def _distribute_round_robin(self, chunks_count: int, peers: List[PeerInfo]) -> Dict[int, str]:
        """
        Distribution simple en round-robin: chunk 0 → peer 0, chunk 1 → peer 1, etc.
        Le peer local reçoit aussi sa part équitable.
        
        Args:
            chunks_count: Nombre total de chunks
            peers: Liste des peers disponibles (sans le peer local)
            
        Returns:
            {chunk_index: peer_id}
        """
        my_peer_id = self.config['peer']['id']
        all_peers = [my_peer_id] + [peer.id for peer in peers]
        
        distribution = {}
        for chunk_index in range(chunks_count):
            peer_index = chunk_index % len(all_peers)
            distribution[chunk_index] = all_peers[peer_index]
        
        logger.debug(f"Distribution round-robin: {chunks_count} chunks → {len(all_peers)} peers")
        return distribution
    
    def _distribute_balanced(self, chunks_count: int, peers: List[PeerInfo]) -> Dict[int, str]:
        """
        Distribution équilibrée tenant compte de la capacité de chaque peer.
        TODO: Pour l'instant identique à round_robin, à améliorer avec métrique de charge.
        
        Args:
            chunks_count: Nombre total de chunks
            peers: Liste des peers disponibles
            
        Returns:
            {chunk_index: peer_id}
        """
        # Pour l'instant, utiliser round-robin
        # Future amélioration: tenir compte de l'espace disque, bande passante, etc.
        return self._distribute_round_robin(chunks_count, peers)
    
    def _send_chunk_to_peer(
        self, 
        peer_id: str, 
        file_id: str, 
        chunk_index: int, 
        chunk_data: bytes,
        chunk_hash: str
    ) -> bool:
        """
        Envoie un chunk à un peer distant via API.
        
        Args:
            peer_id: ID du peer destinataire
            file_id: ID du fichier
            chunk_index: Index du chunk
            chunk_data: Données brutes du chunk
            chunk_hash: Hash SHA-256 du chunk
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Récupérer l'adresse du peer
            peer_info = self.cache_manager.get_peer_info(peer_id)
            if not peer_info:
                logger.error(f"Peer {peer_id} introuvable dans le cache")
                return False
            
            # Endpoint pour stocker un chunk
            url = f"http://{peer_info.host}:{peer_info.port}/api/chunks/store"
            
            # Préparer la requête
            files = {'chunk_data': ('chunk', chunk_data, 'application/octet-stream')}
            data = {
                'file_id': file_id,
                'chunk_index': chunk_index,
                'chunk_hash': chunk_hash
            }
            
            # Envoyer
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                logger.debug(f"Chunk {chunk_index} envoyé à peer {peer_id}")
                return True
            else:
                logger.error(f"Erreur envoi chunk {chunk_index} à {peer_id}: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Exception réseau lors de l'envoi du chunk {chunk_index} à {peer_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Exception inattendue lors de l'envoi du chunk {chunk_index}: {e}")
            return False
    
    def receive_chunk(
        self, 
        file_id: str, 
        chunk_index: int, 
        chunk_data: bytes, 
        chunk_hash: str
    ) -> bool:
        """
        Reçoit et stocke un chunk d'un autre peer.
        
        Args:
            file_id: ID du fichier
            chunk_index: Index du chunk
            chunk_data: Données du chunk
            chunk_hash: Hash attendu
            
        Returns:
            True si stockage réussi, False sinon
        """
        try:
            # Vérifier le hash
            actual_hash = calculate_chunk_hash(chunk_data)
            if actual_hash != chunk_hash:
                logger.error(f"Hash invalide pour chunk {chunk_index} du fichier {file_id}")
                return False
            
            # Créer le répertoire pour ce fichier
            file_chunks_dir = self.distributed_chunks_dir / file_id
            file_chunks_dir.mkdir(exist_ok=True)
            
            # Stocker le chunk
            chunk_path = file_chunks_dir / f"chunk_{chunk_index}.bin"
            chunk_path.write_bytes(chunk_data)
            
            # Stocker aussi le hash pour vérification future
            hash_path = file_chunks_dir / f"chunk_{chunk_index}.hash"
            hash_path.write_text(chunk_hash)
            
            logger.info(f"Chunk {chunk_index} du fichier {file_id} stocké localement ({len(chunk_data)} octets)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du stockage du chunk {chunk_index}: {e}")
            return False
    
    def get_stored_chunk(self, file_id: str, chunk_index: int) -> Optional[bytes]:
        """
        Récupère un chunk stocké localement (reçu d'un autre peer).
        
        Args:
            file_id: ID du fichier
            chunk_index: Index du chunk
            
        Returns:
            Données du chunk ou None si introuvable
        """
        try:
            chunk_path = self.distributed_chunks_dir / file_id / f"chunk_{chunk_index}.bin"
            
            if not chunk_path.exists():
                logger.warning(f"Chunk {chunk_index} du fichier {file_id} non trouvé")
                return None
            
            chunk_data = chunk_path.read_bytes()
            logger.debug(f"Chunk {chunk_index} lu depuis le stockage local")
            return chunk_data
            
        except Exception as e:
            logger.error(f"Erreur lecture chunk {chunk_index}: {e}")
            return None
    
    def verify_stored_chunk(self, file_id: str, chunk_index: int) -> bool:
        """
        Vérifie l'intégrité d'un chunk stocké localement.
        
        Args:
            file_id: ID du fichier
            chunk_index: Index du chunk
            
        Returns:
            True si le chunk est valide, False sinon
        """
        try:
            chunk_data = self.get_stored_chunk(file_id, chunk_index)
            if not chunk_data:
                return False
            
            # Lire le hash attendu
            hash_path = self.distributed_chunks_dir / file_id / f"chunk_{chunk_index}.hash"
            if not hash_path.exists():
                logger.warning(f"Hash du chunk {chunk_index} introuvable")
                return False
            
            expected_hash = hash_path.read_text().strip()
            actual_hash = calculate_chunk_hash(chunk_data)
            
            if actual_hash != expected_hash:
                logger.error(f"Chunk {chunk_index} corrompu (hash mismatch)")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification chunk {chunk_index}: {e}")
            return False
    
    def get_chunk_distribution_summary(self, distribution_map: Dict[int, str]) -> Dict[str, List[int]]:
        """
        Crée un résumé de la distribution: peer_id → liste de chunks.
        
        Args:
            distribution_map: {chunk_index: peer_id}
            
        Returns:
            {peer_id: [chunk_indexes]}
        """
        summary = {}
        for chunk_index, peer_id in distribution_map.items():
            if peer_id not in summary:
                summary[peer_id] = []
            summary[peer_id].append(chunk_index)
        
        return summary
