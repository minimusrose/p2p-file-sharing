"""
Classes de transfert de données (DTOs) communes au tracker et aux peers.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class PeerInfo:
    """
    Informations sur un peer.
    """
    id: str
    name: str
    ip_address: str
    port: int
    status: str = 'online'
    registered_at: Optional[str] = None
    last_heartbeat: Optional[str] = None
    files_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire avec peer_id au lieu de id pour l'API."""
        data = asdict(self)
        # Renommer 'id' en 'peer_id' pour compatibilité avec l'API tracker
        if 'id' in data:
            data['peer_id'] = data.pop('id')
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PeerInfo':
        """Crée une instance depuis un dictionnaire."""
        # Si 'peer_id' est présent au lieu de 'id', le renommer
        if 'peer_id' in data and 'id' not in data:
            data['id'] = data.pop('peer_id')
        return cls(**data)


@dataclass
class FileInfo:
    """
    Informations sur un fichier partagé.
    """
    id: str
    name: str
    size: int
    hash: str
    owner_id: str
    owner_name: Optional[str] = None
    owner_status: Optional[str] = None
    owner_online: bool = False
    
    # Fragmentation
    is_chunked: bool = False
    chunk_size: Optional[int] = None
    chunks_count: Optional[int] = None
    chunks_hashes: Optional[str] = None  # JSON stringifié
    
    # Fragmentation distribuée (nouveau)
    is_distributed: bool = False  # True si chunks répartis sur plusieurs peers
    distribution_map: Optional[str] = None  # JSON: {chunk_index: peer_id}
    minimum_peers_required: int = 2  # Nombre minimum de peers pour distribution
    
    # Métadonnées
    shared_at: Optional[str] = None
    download_count: int = 0
    
    # Contrôle d'accès
    allowed_peers: Optional[List[str]] = None  # None ou [] = public, sinon liste des peer_id autorisés
    is_private: bool = False  # Indicateur rapide : True si partage sélectif
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileInfo':
        """Crée une instance depuis un dictionnaire, en ignorant les champs inconnus."""
        import inspect
        # Obtenir les noms des champs du dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        # Filtrer seulement les champs valides
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def get_chunks_hashes_list(self) -> List[str]:
        """
        Retourne la liste des hashes de chunks.
        """
        if not self.chunks_hashes:
            return []
        
        import json
        try:
            return json.loads(self.chunks_hashes)
        except:
            return []


@dataclass
class ChunkInfo:
    """
    Informations sur un chunk de fichier.
    """
    index: int
    size: int
    hash: str
    offset: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkInfo':
        """Crée une instance depuis un dictionnaire."""
        return cls(**data)


@dataclass
class DownloadJob:
    """
    Représente un téléchargement en cours ou terminé.
    """
    id: str
    file_info: FileInfo
    source_peer: PeerInfo
    destination_path: str
    
    # État
    status: str = 'pending'  # pending, downloading, paused, completed, failed, cancelled
    progress: float = 0.0  # Pourcentage (0-100)
    bytes_downloaded: int = 0
    download_speed: float = 0.0  # octets/seconde
    
    # Chunks (si fichier fragmenté)
    chunks_status: Optional[Dict[int, str]] = None  # {chunk_index: 'pending'|'downloading'|'completed'|'failed'}
    
    # Chunks distribués (nouveau - pour fragmentation distribuée)
    chunks_progress: Optional[Dict[int, Dict[str, Any]]] = None  # {chunk_index: {'status': ..., 'peer_id': ..., 'progress': ...}}
    missing_peers: Optional[List[str]] = None  # Liste des peer_id hors ligne
    auto_resume: bool = True  # Reprise automatique quand peers reviennent
    
    # Timestamps
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Erreurs
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        data = asdict(self)
        # Convertir les objets imbriqués
        data['file_info'] = self.file_info.to_dict()
        data['source_peer'] = self.source_peer.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadJob':
        """Crée une instance depuis un dictionnaire."""
        # Reconstruire les objets imbriqués
        file_info = FileInfo.from_dict(data.pop('file_info'))
        source_peer = PeerInfo.from_dict(data.pop('source_peer'))
        return cls(file_info=file_info, source_peer=source_peer, **data)
    
    def update_progress(self, bytes_downloaded: int, total_size: int):
        """
        Met à jour la progression du téléchargement.
        """
        self.bytes_downloaded = bytes_downloaded
        if total_size > 0:
            self.progress = (bytes_downloaded / total_size) * 100
    
    def is_completed(self) -> bool:
        """Vérifie si le téléchargement est terminé."""
        return self.status == 'completed'
    
    def is_failed(self) -> bool:
        """Vérifie si le téléchargement a échoué."""
        return self.status in ['failed', 'cancelled']


@dataclass
class UDPAnnouncement:
    """
    Message d'annonce UDP pour la découverte locale.
    """
    type: str  # ANNOUNCE, QUERY, RESPONSE, GOODBYE
    peer_id: str
    peer_name: str
    ip: str
    port: int
    files: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UDPAnnouncement':
        """Crée une instance depuis un dictionnaire."""
        return cls(**data)
    
    def to_json(self) -> str:
        """Convertit en JSON."""
        import json
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UDPAnnouncement':
        """Crée une instance depuis JSON."""
        import json
        return cls.from_dict(json.loads(json_str))


@dataclass
class SearchQuery:
    """
    Requête de recherche de fichiers.
    """
    query: str
    limit: int = 50
    file_type: Optional[str] = None  # documents, images, videos, etc.
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    only_online: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)


@dataclass
class TrackerStatus:
    """
    Statut de connexion au tracker.
    """
    is_connected: bool
    last_heartbeat: Optional[float] = None
    reconnect_attempts: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return asdict(self)