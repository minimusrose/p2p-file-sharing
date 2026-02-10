"""
Modèles de données pour le tracker.
"""

from datetime import datetime
from typing import List, Optional
from tracker import db
from shared.constants import PEER_STATUS_ONLINE, PEER_STATUS_OFFLINE
from werkzeug.security import generate_password_hash, check_password_hash


class Peer(db.Model):
    """
    Représente un peer (étudiant) connecté au réseau.
    """
    __tablename__ = 'peers'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4 ou IPv6
    port = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default=PEER_STATUS_ONLINE)
    
    # Timestamps
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    files = db.relationship('File', backref='owner', lazy=True, cascade='all, delete-orphan')
    downloads_as_source = db.relationship('Download', 
                                         foreign_keys='Download.source_peer_id',
                                         backref='source_peer', 
                                         lazy=True)
    downloads_as_destination = db.relationship('Download',
                                              foreign_keys='Download.destination_peer_id',
                                              backref='destination_peer',
                                              lazy=True)
    
    def __repr__(self):
        return f'<Peer {self.name} ({self.ip_address}:{self.port})>'
    
    def to_dict(self):
        """Convertit le peer en dictionnaire."""
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'port': self.port,
            'status': self.status,
            'registered_at': self.registered_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'files_count': len(self.files)
        }
    
    def is_online(self, timeout_seconds: int = 60) -> bool:
        """
        Vérifie si le peer est considéré comme en ligne.
        
        Args:
            timeout_seconds: Délai après lequel un peer est considéré hors ligne
            
        Returns:
            True si en ligne, False sinon
        """
        if self.status == PEER_STATUS_OFFLINE:
            return False
        
        time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return time_since_heartbeat <= timeout_seconds
    
    def update_heartbeat(self):
        """Met à jour le timestamp du dernier heartbeat."""
        self.last_heartbeat = datetime.utcnow()
        self.status = PEER_STATUS_ONLINE


class File(db.Model):
    """
    Représente un fichier partagé sur le réseau.
    """
    __tablename__ = 'files'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(db.String(255), nullable=False)
    size = db.Column(db.BigInteger, nullable=False)  # Taille en octets
    hash = db.Column(db.String(64), nullable=False, index=True)  # SHA256
    
    # Informations sur la fragmentation
    is_chunked = db.Column(db.Boolean, default=False)
    chunk_size = db.Column(db.Integer, nullable=True)
    chunks_count = db.Column(db.Integer, nullable=True)
    chunks_hashes = db.Column(db.Text, nullable=True)  # JSON stringifié
    
    # Relations
    owner_id = db.Column(db.String(36), db.ForeignKey('peers.id'), nullable=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # User qui a uploadé via web
    
    # Métadonnées
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    
    # Contrôle d'accès
    is_private = db.Column(db.Boolean, default=False, index=True)  # Partage sélectif activé ?
    allowed_peers = db.Column(db.Text, nullable=True)  # JSON stringifié : liste des peer_id autorisés
    
    # Relations
    downloads = db.relationship('Download', backref='file', lazy=True)
    
    def __repr__(self):
        return f'<File {self.name} ({self.size} bytes)>'
    
    def to_dict(self):
        """Convertit le fichier en dictionnaire."""
        import json
        
        # Parser allowed_peers si présent
        allowed_peers_list = None
        if self.allowed_peers:
            try:
                allowed_peers_list = json.loads(self.allowed_peers)
            except:
                allowed_peers_list = None
        
        return {
            'id': self.id,
            'name': self.name,
            'size': self.size,
            'hash': self.hash,
            'is_chunked': self.is_chunked,
            'chunk_size': self.chunk_size,
            'chunks_count': self.chunks_count,
            'chunks_hashes': self.chunks_hashes,
            'owner_id': self.owner_id,
            'owner_name': self.owner.name if self.owner else None,
            'owner_ip': self.owner.ip_address if self.owner else None,
            'owner_port': self.owner.port if self.owner else None,
            'owner_status': self.owner.status if self.owner else None,
            'shared_at': self.shared_at.isoformat(),
            'download_count': self.download_count,
            'is_private': self.is_private,
            'allowed_peers': allowed_peers_list
        }
    
    def increment_download_count(self):
        """Incrémente le compteur de téléchargements."""
        self.download_count += 1


class Download(db.Model):
    """
    Représente un téléchargement effectué entre deux peers.
    """
    __tablename__ = 'downloads'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    
    # Relations
    file_id = db.Column(db.String(36), db.ForeignKey('files.id'), nullable=False)
    source_peer_id = db.Column(db.String(36), db.ForeignKey('peers.id'), nullable=False)
    destination_peer_id = db.Column(db.String(36), db.ForeignKey('peers.id'), nullable=False)
    
    # Informations sur le téléchargement
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # pending, downloading, completed, failed
    bytes_transferred = db.Column(db.BigInteger, default=0)
    
    def __repr__(self):
        return f'<Download {self.file.name if self.file else "?"} from {self.source_peer_id} to {self.destination_peer_id}>'
    
    def to_dict(self):
        """Convertit le téléchargement en dictionnaire."""
        return {
            'id': self.id,
            'file_id': self.file_id,
            'file_name': self.file.name if self.file else None,
            'source_peer_id': self.source_peer_id,
            'source_peer_name': self.source_peer.name if self.source_peer else None,
            'destination_peer_id': self.destination_peer_id,
            'destination_peer_name': self.destination_peer.name if self.destination_peer else None,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'bytes_transferred': self.bytes_transferred
        }


class Statistics(db.Model):
    """
    Statistiques globales du système.
    """
    __tablename__ = 'statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Compteurs
    total_peers_registered = db.Column(db.Integer, default=0)
    total_files_shared = db.Column(db.Integer, default=0)
    total_downloads = db.Column(db.Integer, default=0)
    total_bytes_transferred = db.Column(db.BigInteger, default=0)
    
    # Timestamp
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Statistics: {self.total_peers_registered} peers, {self.total_files_shared} files>'
    
    def to_dict(self):
        """Convertit les statistiques en dictionnaire."""
        return {
            'total_peers_registered': self.total_peers_registered,
            'total_files_shared': self.total_files_shared,
            'total_downloads': self.total_downloads,
            'total_bytes_transferred': self.total_bytes_transferred,
            'last_updated': self.last_updated.isoformat()
        }
    
    @staticmethod
    def get_or_create():
        """Récupère ou crée l'instance unique de statistiques."""
        stats = Statistics.query.first()
        if not stats:
            stats = Statistics()
            db.session.add(stats)
            db.session.commit()
        return stats


class User(db.Model):
    """
    Représente un utilisateur avec compte (pour l'interface web).
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Rôles et permissions
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Association optionnelle avec un peer
    peer_id = db.Column(db.String(36), db.ForeignKey('peers.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password: str):
        """Hash et stocke le mot de passe."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Vérifie si le mot de passe est correct."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convertit l'utilisateur en dictionnaire."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'peer_id': self.peer_id,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @staticmethod
    def create_admin_if_not_exists():
        """Crée un compte admin par défaut si aucun utilisateur n'existe."""
        if User.query.count() == 0:
            admin = User(
                username='admin',
                email='admin@p2p.local',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            return True
        return False