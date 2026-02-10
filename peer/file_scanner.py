"""
Scanner de fichiers pour détecter et indexer les fichiers partagés.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Callable, Optional
from datetime import datetime
import time
from threading import Thread, Event

from shared.models import FileInfo
from shared.crypto import calculate_file_hash
from shared.utils import get_file_extension, generate_unique_id, format_file_size

logger = logging.getLogger(__name__)


class FileScanner:
    """
    Scanner de fichiers qui surveille un dossier et indexe les fichiers partagés.
    """
    
    def __init__(self, shared_folder: str, config: dict):
        """
        Initialise le scanner.
        
        Args:
            shared_folder: Chemin du dossier à surveiller
            config: Configuration de l'application
        """
        # Convertir en chemin absolu pour éviter les problèmes de chemin relatif
        self.shared_folder = Path(shared_folder).resolve()
        self.config = config
        
        # Index des fichiers {file_id: FileInfo}
        self.files_index: Dict[str, FileInfo] = {}
        
        # Callbacks
        self.on_file_added: Optional[Callable] = None
        self.on_file_removed: Optional[Callable] = None
        self.on_file_modified: Optional[Callable] = None
        
        # Thread de scan automatique
        self._scan_thread: Optional[Thread] = None
        self._stop_event = Event()
        
        # Créer le dossier s'il n'existe pas
        self.shared_folder.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Scanner initialisé pour : {self.shared_folder}")
    
    def scan_files(self) -> List[FileInfo]:
        """
        Scan complet du dossier partagé.
        
        Returns:
            Liste des fichiers trouvés
        """
        logger.info(f"Scan du dossier : {self.shared_folder}")
        
        new_files = {}
        scanned_count = 0
        
        try:
            # Parcourir tous les fichiers
            for filepath in self.shared_folder.rglob('*'):
                # Ignorer les dossiers et fichiers cachés
                if filepath.is_dir() or filepath.name.startswith('.'):
                    continue
                
                try:
                    # Obtenir les informations du fichier
                    file_info = self._create_file_info(filepath)
                    new_files[file_info.id] = file_info
                    scanned_count += 1
                    
                except Exception as e:
                    logger.error(f"Erreur lors du scan de {filepath}: {e}")
            
            # Détecter les changements
            added, removed, modified = self._compare_indexes(self.files_index, new_files)
            
            # Mettre à jour l'index
            self.files_index = new_files
            
            # Notifier les changements
            self._notify_changes(added, removed, modified)
            
            logger.info(f"Scan terminé : {scanned_count} fichiers trouvés, "
                       f"{len(added)} ajoutés, {len(removed)} supprimés, {len(modified)} modifiés")
            
            return list(self.files_index.values())
            
        except Exception as e:
            logger.error(f"Erreur lors du scan : {e}")
            return []
    
    def _create_file_info(self, filepath: Path) -> FileInfo:
        """
        Crée un objet FileInfo pour un fichier.
        
        Args:
            filepath: Chemin du fichier
            
        Returns:
            FileInfo créé
        """
        # Calculer le hash
        hash_algo = self.config['security']['hash_algorithm']
        file_hash = calculate_file_hash(filepath, hash_algo)
        
        # Obtenir la taille
        file_size = filepath.stat().st_size
        
        # Nom relatif au dossier partagé
        relative_name = str(filepath.relative_to(self.shared_folder))
        
        # Déterminer si le fichier doit être fragmenté
        chunking_config = self.config['chunking']
        should_chunk = (chunking_config['enabled'] and 
                       file_size > chunking_config['threshold_size'])
        
        # Générer un ID persistant basé sur le hash du fichier
        # Cela garantit que le même fichier aura toujours le même ID
        import hashlib
        file_id = hashlib.sha256(file_hash.encode()).hexdigest()[:36]
        
        # Créer FileInfo
        file_info = FileInfo(
            id=file_id,
            name=relative_name,
            size=file_size,
            hash=file_hash,
            owner_id='',  # Sera rempli par le peer
            is_chunked=should_chunk,
            shared_at=datetime.now().isoformat()
        )
        
        # Calculer les informations de chunking si nécessaire
        if should_chunk:
            from peer.chunk_manager import ChunkManager
            chunk_manager = ChunkManager(self.config)
            
            chunk_size = chunking_config['chunk_size']
            chunks_count = chunk_manager.calculate_chunks_count(file_size, chunk_size)
            
            file_info.chunk_size = chunk_size
            file_info.chunks_count = chunks_count
            # Les hashes de chunks seront calculés à la demande
        
        return file_info
    
    def _compare_indexes(self, old_index: Dict[str, FileInfo], 
                        new_index: Dict[str, FileInfo]) -> tuple:
        """
        Compare deux index pour détecter les changements.
        
        Args:
            old_index: Ancien index
            new_index: Nouvel index
            
        Returns:
            Tuple (added, removed, modified)
        """
        # Créer des index par hash pour comparaison
        old_by_hash = {f.hash: f for f in old_index.values()}
        new_by_hash = {f.hash: f for f in new_index.values()}
        
        # Fichiers ajoutés
        added = [f for h, f in new_by_hash.items() if h not in old_by_hash]
        
        # Fichiers supprimés
        removed = [f for h, f in old_by_hash.items() if h not in new_by_hash]
        
        # Fichiers modifiés (même nom mais hash différent)
        modified = []
        for new_file in new_index.values():
            for old_file in old_index.values():
                if (new_file.name == old_file.name and 
                    new_file.hash != old_file.hash):
                    modified.append(new_file)
                    break
        
        return (added, removed, modified)
    
    def _notify_changes(self, added: List[FileInfo], removed: List[FileInfo], 
                       modified: List[FileInfo]):
        """
        Notifie les callbacks des changements détectés.
        
        Args:
            added: Fichiers ajoutés
            removed: Fichiers supprimés
            modified: Fichiers modifiés
        """
        if self.on_file_added:
            for file_info in added:
                try:
                    self.on_file_added(file_info)
                except Exception as e:
                    logger.error(f"Erreur callback on_file_added: {e}")
        
        if self.on_file_removed:
            for file_info in removed:
                try:
                    self.on_file_removed(file_info)
                except Exception as e:
                    logger.error(f"Erreur callback on_file_removed: {e}")
        
        if self.on_file_modified:
            for file_info in modified:
                try:
                    self.on_file_modified(file_info)
                except Exception as e:
                    logger.error(f"Erreur callback on_file_modified: {e}")
    
    def get_files(self) -> List[FileInfo]:
        """
        Retourne la liste des fichiers indexés.
        
        Returns:
            Liste des FileInfo
        """
        return list(self.files_index.values())
    
    def get_file_by_id(self, file_id: str) -> Optional[FileInfo]:
        """
        Récupère un fichier par son ID.
        
        Args:
            file_id: ID du fichier
            
        Returns:
            FileInfo ou None si non trouvé
        """
        return self.files_index.get(file_id)
    
    def get_file_path(self, file_info: FileInfo) -> Path:
        """
        Obtient le chemin complet d'un fichier.
        
        Args:
            file_info: Informations du fichier
            
        Returns:
            Path complet du fichier
        """
        return self.shared_folder / file_info.name
    
    def start_auto_scan(self, interval: int = None):
        """
        Démarre le scan automatique en arrière-plan.
        
        Args:
            interval: Intervalle en secondes (None = utilise config)
        """
        if self._scan_thread and self._scan_thread.is_alive():
            logger.warning("Le scan automatique est déjà démarré")
            return
        
        if interval is None:
            interval = self.config['peer']['scanner']['auto_scan_interval']
        
        self._stop_event.clear()
        self._scan_thread = Thread(target=self._auto_scan_loop, args=(interval,))
        self._scan_thread.daemon = True
        self._scan_thread.start()
        
        logger.info(f"Scan automatique démarré (intervalle: {interval}s)")
    
    def stop_auto_scan(self):
        """
        Arrête le scan automatique.
        """
        if not self._scan_thread or not self._scan_thread.is_alive():
            return
        
        logger.info("Arrêt du scan automatique...")
        self._stop_event.set()
        self._scan_thread.join(timeout=5)
        logger.info("Scan automatique arrêté")
    
    def _auto_scan_loop(self, interval: int):
        """
        Boucle de scan automatique.
        
        Args:
            interval: Intervalle entre les scans
        """
        while not self._stop_event.is_set():
            try:
                self.scan_files()
            except Exception as e:
                logger.error(f"Erreur dans la boucle de scan automatique: {e}")
            
            # Attendre l'intervalle ou l'arrêt
            self._stop_event.wait(interval)
    
    def get_statistics(self) -> dict:
        """
        Retourne des statistiques sur les fichiers.
        
        Returns:
            Dictionnaire de statistiques
        """
        files = self.get_files()
        
        if not files:
            return {
                'total_files': 0,
                'total_size': 0,
                'total_size_formatted': '0 B',
                'by_extension': {},
                'largest_file': None,
                'chunked_files': 0
            }
        
        total_size = sum(f.size for f in files)
        chunked_count = sum(1 for f in files if f.is_chunked)
        
        # Statistiques par extension
        by_extension = {}
        for file in files:
            ext = get_file_extension(file.name)
            if ext not in by_extension:
                by_extension[ext] = {'count': 0, 'size': 0}
            by_extension[ext]['count'] += 1
            by_extension[ext]['size'] += file.size
        
        # Fichier le plus gros
        largest = max(files, key=lambda f: f.size)
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'total_size_formatted': format_file_size(total_size),
            'by_extension': by_extension,
            'largest_file': {
                'name': largest.name,
                'size': largest.size,
                'size_formatted': format_file_size(largest.size)
            },
            'chunked_files': chunked_count
        }