"""
Gestionnaire de cache local pour stocker les informations des peers et fichiers.
Permet le fonctionnement en mode dégradé sans tracker.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from threading import Lock

from shared.models import PeerInfo, FileInfo

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gère le cache local des peers et fichiers découverts.
    """
    
    def __init__(self, db_path: str):
        """
        Initialise le gestionnaire de cache.
        
        Args:
            db_path: Chemin de la base de données SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = Lock()
        self._init_database()
        
        logger.info(f"Cache initialisé : {self.db_path}")
    
    def _init_database(self):
        """
        Initialise les tables de la base de données.
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Table des peers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS peers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    status TEXT DEFAULT 'online',
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    discovery_method TEXT,
                    data TEXT
                )
            ''')
            
            # Table des fichiers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    hash TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    is_chunked BOOLEAN DEFAULT 0,
                    chunk_size INTEGER,
                    chunks_count INTEGER,
                    chunks_hashes TEXT,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    FOREIGN KEY (owner_id) REFERENCES peers(id)
                )
            ''')
            
            # Index pour améliorer les performances
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_owner ON files(owner_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_peers_status ON peers(status)')
            
            conn.commit()
            conn.close()
            
            logger.info("Base de données du cache initialisée")
    
    def add_peer(self, peer: PeerInfo, discovery_method: str = 'unknown'):
        """
        Ajoute ou met à jour un peer dans le cache.
        
        Args:
            peer: Informations du peer
            discovery_method: Méthode de découverte ('tracker', 'udp', 'manual')
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO peers 
                (id, name, ip_address, port, status, last_seen, discovery_method, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                peer.id,
                peer.name,
                peer.ip_address,
                peer.port,
                peer.status,
                datetime.now().isoformat(),
                discovery_method,
                json.dumps(peer.to_dict())
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Peer ajouté au cache : {peer.name} via {discovery_method}")
    
    def get_peer(self, peer_id: str) -> Optional[PeerInfo]:
        """
        Récupère un peer par son ID.
        
        Args:
            peer_id: ID du peer
            
        Returns:
            PeerInfo ou None si non trouvé
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT data FROM peers WHERE id = ?', (peer_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return PeerInfo.from_dict(json.loads(row[0]))
            return None
    
    def get_all_peers(self, only_online: bool = False, 
                     max_age_hours: int = 24) -> List[PeerInfo]:
        """
        Récupère tous les peers du cache.
        
        Args:
            only_online: Ne retourner que les peers en ligne
            max_age_hours: Âge maximum des entrées (en heures)
            
        Returns:
            Liste de PeerInfo
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Calculer la date limite
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            
            query = 'SELECT data FROM peers WHERE last_seen > ?'
            params = [cutoff.isoformat()]
            
            if only_online:
                query += ' AND status = ?'
                params.append('online')
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            peers = [PeerInfo.from_dict(json.loads(row[0])) for row in rows]
            return peers
    
    def remove_peer(self, peer_id: str):
        """
        Supprime un peer du cache.
        
        Args:
            peer_id: ID du peer
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM peers WHERE id = ?', (peer_id,))
            cursor.execute('DELETE FROM files WHERE owner_id = ?', (peer_id,))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Peer supprimé du cache : {peer_id}")
    
    def add_file(self, file: FileInfo):
        """
        Ajoute ou met à jour un fichier dans le cache.
        
        Args:
            file: Informations du fichier
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO files 
                    (id, name, size, hash, owner_id, is_chunked, chunk_size, 
                     chunks_count, chunks_hashes, last_seen, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file.id,
                    file.name,
                    file.size,
                    file.hash,
                    file.owner_id,
                    file.is_chunked,
                    file.chunk_size,
                    file.chunks_count,
                    file.chunks_hashes,
                    datetime.now().isoformat(),
                    json.dumps(file.to_dict())
                ))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"Fichier ajouté au cache : {file.name}")
        except sqlite3.OperationalError as e:
            logger.warning(f"Impossible d'ajouter le fichier au cache (table pas encore créée?) : {e}")
        except Exception as e:
            logger.error(f"Erreur ajout fichier au cache : {e}")
    
    def get_file(self, file_id: str) -> Optional[FileInfo]:
        """
        Récupère un fichier par son ID.
        
        Args:
            file_id: ID du fichier
            
        Returns:
            FileInfo ou None si non trouvé
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT data FROM files WHERE id = ?', (file_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return FileInfo.from_dict(json.loads(row[0]))
            return None
    
    def search_files(self, query: str, limit: int = 50) -> List[FileInfo]:
        """
        Recherche des fichiers par nom.
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de FileInfo
        """
        try:
            with self._lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT data FROM files 
                    WHERE name LIKE ? 
                    ORDER BY last_seen DESC 
                    LIMIT ?
                ''', (f'%{query}%', limit))
                
                rows = cursor.fetchall()
                conn.close()
                
                files = [FileInfo.from_dict(json.loads(row[0])) for row in rows]
                return files
        except sqlite3.OperationalError as e:
            logger.warning(f"Erreur recherche cache (table peut-être pas encore créée) : {e}")
            return []
        except Exception as e:
            logger.error(f"Erreur inattendue recherche cache : {e}")
            return []
    
    def get_files_by_peer(self, peer_id: str) -> List[FileInfo]:
        """
        Récupère tous les fichiers d'un peer.
        
        Args:
            peer_id: ID du peer
            
        Returns:
            Liste de FileInfo
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('SELECT data FROM files WHERE owner_id = ?', (peer_id,))
            rows = cursor.fetchall()
            
            conn.close()
            
            files = [FileInfo.from_dict(json.loads(row[0])) for row in rows]
            return files
    
    def remove_file(self, file_id: str):
        """
        Supprime un fichier du cache.
        
        Args:
            file_id: ID du fichier
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Fichier supprimé du cache : {file_id}")
    
    def cleanup_old_entries(self, max_age_hours: int = 24):
        """
        Nettoie les entrées trop anciennes du cache.
        
        Args:
            max_age_hours: Âge maximum en heures
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Supprimer les peers anciens
            cursor.execute('DELETE FROM peers WHERE last_seen < ?', 
                          (cutoff.isoformat(),))
            peers_deleted = cursor.rowcount
            
            # Supprimer les fichiers orphelins
            cursor.execute('''
                DELETE FROM files 
                WHERE owner_id NOT IN (SELECT id FROM peers)
            ''')
            orphan_files = cursor.rowcount
            
            # Supprimer les fichiers anciens
            cursor.execute('DELETE FROM files WHERE last_seen < ?',
                          (cutoff.isoformat(),))
            old_files = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Nettoyage du cache : {peers_deleted} peers, "
                       f"{orphan_files} fichiers orphelins, {old_files} fichiers anciens")
    
    def get_statistics(self) -> dict:
        """
        Retourne des statistiques sur le cache.
        
        Returns:
            Dictionnaire de statistiques
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Compter les peers
            cursor.execute('SELECT COUNT(*) FROM peers')
            total_peers = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM peers WHERE status = ?', ('online',))
            online_peers = cursor.fetchone()[0]
            
            # Compter les fichiers
            cursor.execute('SELECT COUNT(*) FROM files')
            total_files = cursor.fetchone()[0]
            
            # Méthodes de découverte
            cursor.execute('''
                SELECT discovery_method, COUNT(*) 
                FROM peers 
                GROUP BY discovery_method
            ''')
            discovery_methods = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_peers': total_peers,
                'online_peers': online_peers,
                'offline_peers': total_peers - online_peers,
                'total_files': total_files,
                'discovery_methods': discovery_methods
            }
    
    def clear_all(self):
        """
        Efface toutes les données du cache.
        ATTENTION : Action irréversible !
        """
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM files')
            cursor.execute('DELETE FROM peers')
            
            conn.commit()
            conn.close()
            
            logger.warning("Cache complètement effacé")