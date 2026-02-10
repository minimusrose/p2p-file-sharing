"""
Module Peer - Application client P2P pour partager et télécharger des fichiers.

Le peer peut fonctionner en mode normal (avec tracker) ou en mode dégradé (découverte UDP).
"""

__version__ = '1.0.0'

from flask import Flask
from shared.utils import load_config, setup_logging
import logging

logger = logging.getLogger(__name__)

# Instance globale du peer
_peer_instance = None


def create_app(config_path: str = 'config.yaml') -> Flask:
    """
    Factory pour créer l'application Flask du peer.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Instance de l'application Flask configurée
    """
    # Charger la configuration
    config = load_config(config_path)
    
    # Configurer les logs
    setup_logging(config)
    
    # Créer l'application Flask
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configuration
    app.config['SECRET_KEY'] = 'peer-secret-key-change-in-production'
    app.config['APP_CONFIG'] = config
    
    return app


def get_peer_instance():
    """
    Retourne l'instance globale du peer.
    
    Returns:
        Instance PeerApplication ou None
    """
    return _peer_instance


def set_peer_instance(peer):
    """
    Définit l'instance globale du peer.
    
    Args:
        peer: Instance PeerApplication
    """
    global _peer_instance
    _peer_instance = peer