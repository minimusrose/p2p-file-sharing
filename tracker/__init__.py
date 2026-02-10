"""
Module Tracker - Serveur central de coordination du réseau P2P.

Le tracker maintient une liste des peers connectés et des fichiers disponibles.
Il fournit une API REST pour l'enregistrement des peers et la recherche de fichiers.
"""

__version__ = '1.0.0'

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Instance globale de la base de données
db = SQLAlchemy()


def create_app(config_path: str = 'config.yaml') -> Flask:
    """
    Factory pour créer l'application Flask du tracker.
    
    Args:
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Instance de l'application Flask configurée
    """
    import os
    from shared.utils import load_config, setup_logging
    
    # Charger la configuration
    config = load_config(config_path)
    
    # Configurer les logs
    setup_logging(config)
    
    # Créer l'application Flask
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='../static')
    
    # Configuration de la base de données
    db_uri = config['tracker']['database']['uri']
    
    # Convertir les chemins relatifs SQLite en chemins absolus
    if db_uri.startswith('sqlite:///') and not db_uri.startswith('sqlite:////'):
        # Extraire le chemin relatif après sqlite:///
        db_path = db_uri.replace('sqlite:///', '', 1)
        # Convertir en chemin absolu
        abs_db_path = os.path.abspath(db_path)
        # Créer le répertoire parent si nécessaire
        os.makedirs(os.path.dirname(abs_db_path), exist_ok=True)
        # Reconstituer l'URI avec le chemin absolu
        db_uri = f'sqlite:///{abs_db_path}'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Clé secrète pour les sessions
    app.config['SECRET_KEY'] = config.get('security', {}).get('secret_key', os.urandom(24).hex())
    
    # Stocker la config dans l'app
    app.config['APP_CONFIG'] = config
    
    # Initialiser la base de données
    db.init_app(app)
    
    return app

