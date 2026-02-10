"""
Configuration et gestion de la base de données du tracker.
"""

import logging
import os
from typing import Optional
from flask import Flask
from tracker import db

logger = logging.getLogger(__name__)


def init_database(app: Flask) -> None:
    """
    Initialise la base de données et crée les tables.
    
    Args:
        app: Instance de l'application Flask
    """
    with app.app_context():
        try:
            # Créer le dossier data s'il n'existe pas
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                # Extraire le chemin du fichier
                db_path = db_uri.replace('sqlite:///', '')
                # Gérer les chemins relatifs commençant par ./
                if db_path.startswith('./'):
                    db_path = db_path[2:]
                
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir)
                    logger.info(f"Dossier de base de données créé : {db_dir}")
            
            # Créer toutes les tables
            db.create_all()
            logger.info("Base de données initialisée avec succès")
            
            # Vérifier si le fichier a bien été créé
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '').replace('./', '')
                if os.path.exists(db_path):
                    logger.info(f"Fichier de base de données créé : {db_path}")
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise


def drop_all_tables(app: Flask) -> None:
    """
    Supprime toutes les tables de la base de données.
    ATTENTION: À utiliser uniquement en développement!
    
    Args:
        app: Instance de l'application Flask
    """
    with app.app_context():
        try:
            db.drop_all()
            logger.warning("Toutes les tables ont été supprimées")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des tables: {e}")
            raise


def reset_database(app: Flask) -> None:
    """
    Réinitialise complètement la base de données.
    ATTENTION: Supprime toutes les données!
    
    Args:
        app: Instance de l'application Flask
    """
    logger.warning("Réinitialisation de la base de données...")
    drop_all_tables(app)
    init_database(app)
    logger.info("Base de données réinitialisée")


def get_db_session():
    """
    Retourne la session de base de données.
    
    Returns:
        Session SQLAlchemy
    """
    return db.session


def commit_changes() -> bool:
    """
    Commit les changements dans la base de données.
    
    Returns:
        True si succès, False sinon
    """
    try:
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur lors du commit: {e}")
        db.session.rollback()
        return False


def add_and_commit(obj) -> bool:
    """
    Ajoute un objet et commit.
    
    Args:
        obj: Objet à ajouter
        
    Returns:
        True si succès, False sinon
    """
    try:
        db.session.add(obj)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout: {e}")
        db.session.rollback()
        return False


def delete_and_commit(obj) -> bool:
    """
    Supprime un objet et commit.
    
    Args:
        obj: Objet à supprimer
        
    Returns:
        True si succès, False sinon
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {e}")
        db.session.rollback()
        return False