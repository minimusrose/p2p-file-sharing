"""
Fonctions utilitaires partagées.
"""

import os
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .constants import KB, MB, GB


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    Charge le fichier de configuration YAML.
    
    Args:
        config_path: Chemin vers le fichier config.yaml
        
    Returns:
        Dictionnaire contenant la configuration
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Fichier de configuration introuvable: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Erreur lors de la lecture du fichier de configuration: {e}")


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configure le système de logging.
    
    Args:
        config: Dictionnaire de configuration
    """
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_file = log_config.get('file', 'logs/app.log')
    
    # Créer le dossier de logs s'il n'existe pas
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configuration du logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def format_file_size(size_bytes: int) -> str:
    """
    Formate une taille de fichier en unités lisibles.
    
    Args:
        size_bytes: Taille en octets
        
    Returns:
        Chaîne formatée (ex: "1.5 MB")
    """
    if size_bytes < KB:
        return f"{size_bytes} B"
    elif size_bytes < MB:
        return f"{size_bytes / KB:.2f} KB"
    elif size_bytes < GB:
        return f"{size_bytes / MB:.2f} MB"
    else:
        return f"{size_bytes / GB:.2f} GB"


def format_timestamp(timestamp: Optional[float] = None, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Formate un timestamp en chaîne lisible.
    
    Args:
        timestamp: Timestamp Unix (None = maintenant)
        format_str: Format de sortie
        
    Returns:
        Chaîne formatée
    """
    if timestamp is None:
        dt = datetime.now()
    else:
        dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(format_str)


def ensure_directory_exists(directory: str) -> None:
    """
    Crée un dossier s'il n'existe pas.
    
    Args:
        directory: Chemin du dossier
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def get_file_extension(filename: str) -> str:
    """
    Extrait l'extension d'un fichier.
    
    Args:
        filename: Nom du fichier
        
    Returns:
        Extension (avec le point, ex: '.pdf')
    """
    return Path(filename).suffix.lower()


def get_file_category(filename: str) -> str:
    """
    Détermine la catégorie d'un fichier selon son extension.
    
    Args:
        filename: Nom du fichier
        
    Returns:
        Catégorie ('documents', 'images', etc.) ou 'other'
    """
    from .constants import FILE_CATEGORIES
    
    ext = get_file_extension(filename)
    
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    
    return 'other'


def is_valid_file_size(size_bytes: int, max_size: int) -> bool:
    """
    Vérifie si la taille d'un fichier est valide.
    
    Args:
        size_bytes: Taille du fichier
        max_size: Taille maximale autorisée
        
    Returns:
        True si valide, False sinon
    """
    return 0 < size_bytes <= max_size


def sanitize_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour éviter les problèmes.
    
    Args:
        filename: Nom du fichier original
        
    Returns:
        Nom de fichier nettoyé
    """
    # Remplace les caractères interdits
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limite la longueur
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def calculate_chunks_count(file_size: int, chunk_size: int) -> int:
    """
    Calcule le nombre de chunks nécessaires pour un fichier.
    
    Args:
        file_size: Taille du fichier en octets
        chunk_size: Taille d'un chunk en octets
        
    Returns:
        Nombre de chunks
    """
    return (file_size + chunk_size - 1) // chunk_size


def get_available_disk_space(path: str = '.') -> int:
    """
    Obtient l'espace disque disponible.
    
    Args:
        path: Chemin pour vérifier l'espace
        
    Returns:
        Espace disponible en octets
    """
    import shutil
    stat = shutil.disk_usage(path)
    return stat.free


def generate_unique_id() -> str:
    """
    Génère un identifiant unique.
    
    Returns:
        Chaîne d'identifiant unique
    """
    import uuid
    return str(uuid.uuid4())


def get_or_create_peer_id(storage_path: str = 'data/peer_id.txt') -> str:
    """
    Récupère ou crée un ID peer persistant basé sur l'identité de la machine.
    L'ID est sauvegardé localement et réutilisé à chaque démarrage.
    
    IMPORTANT : 1 Machine = 1 Étudiant = 1 ID persistant
    La variable d'environnement PEER_ID_FILE permet d'utiliser un fichier différent
    (uniquement pour les tests avec plusieurs peers sur la même machine).
    
    Args:
        storage_path: Chemin où sauvegarder l'ID peer
        
    Returns:
        ID peer unique et persistant
    """
    import hashlib
    import uuid
    
    # Permettre de surcharger le chemin via variable d'environnement (pour tests uniquement)
    storage_path = os.environ.get('PEER_ID_FILE', storage_path)
    
    # Vérifier si un ID existe déjà
    if os.path.exists(storage_path):
        try:
            with open(storage_path, 'r', encoding='utf-8') as f:
                peer_id = f.read().strip()
                if peer_id:
                    logging.info(f"ID peer existant récupéré : {peer_id[:8]}...")
                    return peer_id
        except Exception as e:
            logging.warning(f"Erreur lecture ID peer existant : {e}")
    
    # Générer un nouvel ID basé sur l'identité de la machine
    try:
        # Récupérer l'adresse MAC (unique par machine)
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                        for elements in range(0, 8*6, 8)][::-1])
        
        # Combiner avec le hostname pour plus d'unicité
        hostname = get_hostname()
        
        # Pour les tests : si PEER_ID_FILE est défini, ajouter le chemin pour différencier
        # En production : chaque machine aura son propre ID basé uniquement sur MAC + hostname
        unique_string = f"{mac}-{hostname}"
        if os.environ.get('PEER_ID_FILE'):
            # Ajouter le nom du fichier pour créer un ID unique par peer en test
            unique_string += f"-{storage_path}"
        
        # Générer un hash SHA256 pour créer un ID propre
        peer_id = hashlib.sha256(unique_string.encode()).hexdigest()[:32]
        
        # Sauvegarder l'ID pour réutilisation future
        ensure_directory_exists(os.path.dirname(storage_path))
        with open(storage_path, 'w', encoding='utf-8') as f:
            f.write(peer_id)
        
        logging.info(f"Nouvel ID peer généré et sauvegardé : {peer_id[:8]}...")
        return peer_id
        
    except Exception as e:
        logging.error(f"Erreur génération ID peer persistant : {e}")
        # Fallback : générer un UUID standard
        fallback_id = str(uuid.uuid4())
        try:
            ensure_directory_exists(os.path.dirname(storage_path))
            with open(storage_path, 'w', encoding='utf-8') as f:
                f.write(fallback_id)
        except:
            pass
        return fallback_id


def get_hostname() -> str:
    """
    Obtient le nom d'hôte de la machine.
    
    Returns:
        Nom d'hôte
    """
    import socket
    try:
        return socket.gethostname()
    except Exception as e:
        logging.warning(f"Impossible d'obtenir le hostname: {e}")
        return "unknown"