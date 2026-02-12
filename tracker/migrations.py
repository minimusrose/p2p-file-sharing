"""
Migration automatique de la base de données pour ajouter le support des peers web.
Cette migration s'exécute automatiquement au démarrage si nécessaire.
"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)


def check_column_exists(cursor, table_name, column_name):
    """Vérifie si une colonne existe dans une table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns


def migrate_to_peer_web_system(db_path):
    """
    Migration vers le système de peer web (v2.0).
    Ajoute les colonnes is_web_peer et user_id à la table peers.
    
    Args:
        db_path: Chemin vers la base de données SQLite
    """
    if not os.path.exists(db_path):
        logger.info("Base de données inexistante, aucune migration nécessaire")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("🔄 Vérification des migrations nécessaires...")
        
        migrations_applied = []
        
        # Migration 1 : Ajouter is_web_peer
        if not check_column_exists(cursor, 'peers', 'is_web_peer'):
            cursor.execute("""
                ALTER TABLE peers 
                ADD COLUMN is_web_peer BOOLEAN DEFAULT 0
            """)
            migrations_applied.append("is_web_peer")
            logger.info("✅ Colonne 'is_web_peer' ajoutée à la table peers")
        
        # Migration 2 : Ajouter user_id
        if not check_column_exists(cursor, 'peers', 'user_id'):
            cursor.execute("""
                ALTER TABLE peers 
                ADD COLUMN user_id INTEGER
            """)
            migrations_applied.append("user_id")
            logger.info("✅ Colonne 'user_id' ajoutée à la table peers")
        
        if migrations_applied:
            conn.commit()
            logger.info(f"✅ Migration réussie : {', '.join(migrations_applied)}")
        else:
            logger.info("✓ Base de données déjà à jour")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la migration : {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise


def apply_all_migrations(app):
    """
    Applique toutes les migrations nécessaires.
    À appeler après l'initialisation de la base de données.
    
    Args:
        app: Instance Flask
    """
    try:
        # Récupérer le chemin de la base de données depuis la config
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        if not db_uri.startswith('sqlite:///'):
            logger.warning("Migration uniquement supportée pour SQLite")
            return
        
        # Extraire le chemin
        db_path = db_uri.replace('sqlite:///', '')
        if db_path.startswith('./'):
            db_path = db_path[2:]
        
        # Chemin absolu
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.root_path, '..', db_path)
            db_path = os.path.abspath(db_path)
        
        logger.info(f"Chemin de base de données : {db_path}")
        
        # Appliquer les migrations
        migrate_to_peer_web_system(db_path)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'application des migrations : {e}")
        # Ne pas lever d'exception pour ne pas bloquer le démarrage
