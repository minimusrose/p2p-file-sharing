"""
Gestionnaire de fragmentation de fichiers en chunks.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, BinaryIO
from dataclasses import dataclass

from shared.models import FileInfo, ChunkInfo
from shared.crypto import calculate_chunk_hash
from shared.utils import calculate_chunks_count

logger = logging.getLogger(__name__)


class ChunkManager:
    """
    Gère la fragmentation et le réassemblage de fichiers.
    """
    
    def __init__(self, config: dict):
        """
        Initialise le gestionnaire de chunks.
        
        Args:
            config: Configuration de l'application
        """
        self.config = config
        self.chunk_size = config['chunking']['chunk_size']
        self.hash_algorithm = config['security']['hash_algorithm']
    
    def calculate_chunks_count(self, file_size: int, chunk_size: int = None) -> int:
        """
        Calcule le nombre de chunks pour un fichier.
        
        Args:
            file_size: Taille du fichier en octets
            chunk_size: Taille d'un chunk (None = utilise config)
            
        Returns:
            Nombre de chunks
        """
        if chunk_size is None:
            chunk_size = self.chunk_size
        
        return calculate_chunks_count(file_size, chunk_size)
    
    def get_chunk_info(self, file_size: int, chunk_index: int, 
                      chunk_size: int = None) -> ChunkInfo:
        """
        Obtient les informations d'un chunk spécifique.
        
        Args:
            file_size: Taille totale du fichier
            chunk_index: Index du chunk (commence à 0)
            chunk_size: Taille d'un chunk
            
        Returns:
            ChunkInfo avec les détails du chunk
        """
        if chunk_size is None:
            chunk_size = self.chunk_size
        
        offset = chunk_index * chunk_size
        
        # Dernier chunk peut être plus petit
        if chunk_index == self.calculate_chunks_count(file_size, chunk_size) - 1:
            size = file_size - offset
        else:
            size = chunk_size
        
        return ChunkInfo(
            index=chunk_index,
            size=size,
            hash='',  # Sera calculé lors de la lecture
            offset=offset
        )
    
    def read_chunk(self, filepath: Path, chunk_index: int, 
                   file_size: int = None) -> bytes:
        """
        Lit un chunk spécifique d'un fichier.
        
        Args:
            filepath: Chemin du fichier
            chunk_index: Index du chunk
            file_size: Taille du fichier (None = auto-détecte)
            
        Returns:
            Données du chunk (bytes)
        """
        if file_size is None:
            file_size = filepath.stat().st_size
        
        chunk_info = self.get_chunk_info(file_size, chunk_index)
        
        try:
            with open(filepath, 'rb') as f:
                f.seek(chunk_info.offset)
                data = f.read(chunk_info.size)
            
            logger.debug(f"Chunk {chunk_index} lu: {len(data)} octets")
            return data
            
        except Exception as e:
            logger.error(f"Erreur lecture chunk {chunk_index} de {filepath}: {e}")
            raise
    
    def write_chunk(self, filepath: Path, chunk_index: int, data: bytes, 
                    file_size: int):
        """
        Écrit un chunk dans un fichier.
        
        Args:
            filepath: Chemin du fichier
            chunk_index: Index du chunk
            data: Données à écrire
            file_size: Taille totale prévue du fichier
        """
        chunk_info = self.get_chunk_info(file_size, chunk_index)
        
        try:
            # Créer le fichier s'il n'existe pas
            if not filepath.exists():
                # Pré-allouer l'espace
                with open(filepath, 'wb') as f:
                    f.seek(file_size - 1)
                    f.write(b'\0')
            
            # Écrire le chunk
            with open(filepath, 'r+b') as f:
                f.seek(chunk_info.offset)
                written = f.write(data)
            
            logger.debug(f"Chunk {chunk_index} écrit: {written} octets à offset {chunk_info.offset}")
            
        except Exception as e:
            logger.error(f"Erreur écriture chunk {chunk_index} dans {filepath}: {e}")
            raise
    
    def calculate_chunks_hashes(self, filepath: Path) -> List[str]:
        """
        Calcule les hashes de tous les chunks d'un fichier.
        
        Args:
            filepath: Chemin du fichier
            
        Returns:
            Liste des hashes de chunks
        """
        file_size = filepath.stat().st_size
        chunks_count = self.calculate_chunks_count(file_size)
        
        hashes = []
        
        try:
            for i in range(chunks_count):
                data = self.read_chunk(filepath, i, file_size)
                chunk_hash = calculate_chunk_hash(data, self.hash_algorithm)
                hashes.append(chunk_hash)
            
            logger.info(f"Hashes de {chunks_count} chunks calculés pour {filepath.name}")
            return hashes
            
        except Exception as e:
            logger.error(f"Erreur calcul hashes chunks: {e}")
            raise
    
    def verify_chunk(self, filepath: Path, chunk_index: int, 
                    expected_hash: str, file_size: int) -> bool:
        """
        Vérifie l'intégrité d'un chunk.
        
        Args:
            filepath: Chemin du fichier
            chunk_index: Index du chunk
            expected_hash: Hash attendu
            file_size: Taille totale du fichier
            
        Returns:
            True si le chunk est valide, False sinon
        """
        try:
            data = self.read_chunk(filepath, chunk_index, file_size)
            actual_hash = calculate_chunk_hash(data, self.hash_algorithm)
            
            is_valid = actual_hash.lower() == expected_hash.lower()
            
            if not is_valid:
                logger.warning(f"Chunk {chunk_index} invalide: "
                             f"attendu {expected_hash}, obtenu {actual_hash}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Erreur vérification chunk {chunk_index}: {e}")
            return False
    
    def get_chunks_status(self, filepath: Path, expected_hashes: List[str], 
                         file_size: int) -> dict:
        """
        Vérifie le statut de tous les chunks d'un fichier.
        
        Args:
            filepath: Chemin du fichier
            expected_hashes: Liste des hashes attendus
            file_size: Taille totale du fichier
            
        Returns:
            Dictionnaire {chunk_index: 'valid'|'invalid'|'missing'}
        """
        status = {}
        chunks_count = len(expected_hashes)
        
        # Vérifier si le fichier existe
        if not filepath.exists():
            return {i: 'missing' for i in range(chunks_count)}
        
        # Vérifier chaque chunk
        for i in range(chunks_count):
            try:
                if self.verify_chunk(filepath, i, expected_hashes[i], file_size):
                    status[i] = 'valid'
                else:
                    status[i] = 'invalid'
            except Exception:
                status[i] = 'missing'
        
        return status
    
    def prepare_file_info_for_chunking(self, file_info: FileInfo, 
                                      filepath: Path) -> FileInfo:
        """
        Prépare les informations de chunking pour un FileInfo.
        
        Args:
            file_info: FileInfo à enrichir
            filepath: Chemin du fichier
            
        Returns:
            FileInfo mis à jour
        """
        if not file_info.is_chunked:
            return file_info
        
        # Calculer les hashes de chunks
        hashes = self.calculate_chunks_hashes(filepath)
        
        # Mettre à jour le FileInfo
        file_info.chunk_size = self.chunk_size
        file_info.chunks_count = len(hashes)
        file_info.chunks_hashes = json.dumps(hashes)
        
        logger.info(f"Fichier {file_info.name} préparé pour chunking: "
                   f"{file_info.chunks_count} chunks")
        
        return file_info
    
    def get_missing_chunks(self, filepath: Path, expected_hashes: List[str], 
                          file_size: int) -> List[int]:
        """
        Retourne la liste des chunks manquants ou invalides.
        
        Args:
            filepath: Chemin du fichier
            expected_hashes: Hashes attendus
            file_size: Taille du fichier
            
        Returns:
            Liste des index de chunks à télécharger
        """
        status = self.get_chunks_status(filepath, expected_hashes, file_size)
        
        missing = [i for i, s in status.items() if s in ['missing', 'invalid']]
        
        logger.info(f"{len(missing)} chunks manquants/invalides sur {len(status)}")
        
        return missing
    
    def calculate_download_progress(self, filepath: Path, 
                                   expected_hashes: List[str], 
                                   file_size: int) -> float:
        """
        Calcule le pourcentage de téléchargement d'un fichier fragmenté.
        
        Args:
            filepath: Chemin du fichier
            expected_hashes: Hashes attendus
            file_size: Taille du fichier
            
        Returns:
            Pourcentage (0-100)
        """
        status = self.get_chunks_status(filepath, expected_hashes, file_size)
        
        valid_count = sum(1 for s in status.values() if s == 'valid')
        total_count = len(status)
        
        if total_count == 0:
            return 0.0
        
        return (valid_count / total_count) * 100