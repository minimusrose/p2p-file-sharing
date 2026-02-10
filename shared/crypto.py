"""
Fonctions de hashing et cryptographie pour le système P2P.
"""

import hashlib
import logging
from typing import Union, BinaryIO
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_file_hash(filepath: Union[str, Path], algorithm: str = 'sha256', 
                       chunk_size: int = 8192) -> str:
    """
    Calcule le hash d'un fichier entier.
    
    Args:
        filepath: Chemin du fichier
        algorithm: Algorithme de hash ('md5', 'sha1', 'sha256')
        chunk_size: Taille des chunks pour la lecture (en octets)
        
    Returns:
        Hash hexadécimal du fichier
    """
    try:
        # Sélectionner l'algorithme
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha1':
            hasher = hashlib.sha1()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            logger.warning(f"Algorithme {algorithm} non supporté, utilisation de sha256")
            hasher = hashlib.sha256()
        
        # Lire et hasher le fichier par chunks
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                hasher.update(data)
        
        return hasher.hexdigest()
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul du hash de {filepath}: {e}")
        raise


def calculate_chunk_hash(data: bytes, algorithm: str = 'sha256') -> str:
    """
    Calcule le hash d'un chunk de données.
    
    Args:
        data: Données à hasher
        algorithm: Algorithme de hash
        
    Returns:
        Hash hexadécimal
    """
    try:
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha1':
            hasher = hashlib.sha1()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.sha256()
        
        hasher.update(data)
        return hasher.hexdigest()
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul du hash du chunk: {e}")
        raise


def verify_hash(data: Union[bytes, str, Path], expected_hash: str, 
               algorithm: str = 'sha256') -> bool:
    """
    Vérifie si le hash de données correspond au hash attendu.
    
    Args:
        data: Données à vérifier (bytes, chemin de fichier)
        expected_hash: Hash attendu
        algorithm: Algorithme de hash
        
    Returns:
        True si le hash correspond, False sinon
    """
    try:
        if isinstance(data, bytes):
            actual_hash = calculate_chunk_hash(data, algorithm)
        else:
            actual_hash = calculate_file_hash(data, algorithm)
        
        return actual_hash.lower() == expected_hash.lower()
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du hash: {e}")
        return False


def generate_peer_id() -> str:
    """
    Génère un identifiant unique pour un peer.
    
    Returns:
        ID unique (UUID v4)
    """
    import uuid
    return str(uuid.uuid4())


def calculate_multiple_hashes(filepath: Union[str, Path], 
                              algorithms: list = None) -> dict:
    """
    Calcule plusieurs hashes d'un fichier en une seule lecture.
    
    Args:
        filepath: Chemin du fichier
        algorithms: Liste d'algorithmes (['md5', 'sha256'])
        
    Returns:
        Dictionnaire {algorithm: hash}
    """
    if algorithms is None:
        algorithms = ['md5', 'sha256']
    
    hashers = {}
    for algo in algorithms:
        if algo == 'md5':
            hashers[algo] = hashlib.md5()
        elif algo == 'sha1':
            hashers[algo] = hashlib.sha1()
        elif algo == 'sha256':
            hashers[algo] = hashlib.sha256()
    
    try:
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                for hasher in hashers.values():
                    hasher.update(data)
        
        return {algo: hasher.hexdigest() for algo, hasher in hashers.items()}
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul des hashes multiples: {e}")
        raise


def verify_file_integrity(filepath: Union[str, Path], expected_hash: str, 
                         algorithm: str = 'sha256') -> tuple:
    """
    Vérifie l'intégrité complète d'un fichier.
    
    Args:
        filepath: Chemin du fichier
        expected_hash: Hash attendu
        algorithm: Algorithme de hash
        
    Returns:
        Tuple (is_valid: bool, actual_hash: str, error_message: str)
    """
    try:
        # Vérifier que le fichier existe
        if not Path(filepath).exists():
            return (False, '', 'Fichier introuvable')
        
        # Calculer le hash
        actual_hash = calculate_file_hash(filepath, algorithm)
        
        # Comparer
        is_valid = actual_hash.lower() == expected_hash.lower()
        
        if is_valid:
            return (True, actual_hash, '')
        else:
            return (False, actual_hash, 'Hash ne correspond pas')
            
    except Exception as e:
        return (False, '', str(e))


def hash_string(text: str, algorithm: str = 'sha256') -> str:
    """
    Hash une chaîne de caractères.
    
    Args:
        text: Texte à hasher
        algorithm: Algorithme de hash
        
    Returns:
        Hash hexadécimal
    """
    if algorithm == 'md5':
        return hashlib.md5(text.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(text.encode()).hexdigest()
    elif algorithm == 'sha256':
        return hashlib.sha256(text.encode()).hexdigest()
    else:
        return hashlib.sha256(text.encode()).hexdigest()