"""
Système d'authentification pour le tracker.
Gère les comptes utilisateurs, sessions, login/register.
"""

import logging
from datetime import datetime
from flask import session, redirect, url_for, flash
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)


def login_required(f):
    """
    Décorateur pour protéger les routes nécessitant une authentification.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('tracker.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Décorateur pour protéger les routes nécessitant des droits administrateur.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('tracker.login'))
        
        from tracker.database import get_db
        db = get_db()
        user = db.execute(
            'SELECT is_admin FROM users WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        
        if not user or not user['is_admin']:
            flash('Accès réservé aux administrateurs.', 'danger')
            return redirect(url_for('tracker.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def create_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """
    Crée un nouveau compte utilisateur.
    
    Args:
        username: Nom d'utilisateur
        email: Adresse email
        password: Mot de passe en clair
        
    Returns:
        (success: bool, message: str)
    """
    try:
        from tracker.database import get_db
        db = get_db()
        
        # Vérifier si username existe déjà
        existing = db.execute(
            'SELECT id FROM users WHERE username = ? OR email = ?',
            (username, email)
        ).fetchone()
        
        if existing:
            return False, "Ce nom d'utilisateur ou email est déjà utilisé"
        
        # Hash du mot de passe
        password_hash = generate_password_hash(password)
        
        # Créer l'utilisateur
        db.execute(
            '''INSERT INTO users (username, email, password_hash, created_at)
               VALUES (?, ?, ?, ?)''',
            (username, email, password_hash, datetime.now().isoformat())
        )
        db.commit()
        
        logger.info(f"Nouvel utilisateur créé : {username}")
        return True, "Compte créé avec succès"
        
    except Exception as e:
        logger.error(f"Erreur création utilisateur : {e}")
        return False, f"Erreur lors de la création du compte : {str(e)}"


def authenticate_user(username: str, password: str) -> tuple[bool, str, dict]:
    """
    Authentifie un utilisateur.
    
    Args:
        username: Nom d'utilisateur ou email
        password: Mot de passe en clair
        
    Returns:
        (success: bool, message: str, user_data: dict)
    """
    try:
        from tracker.database import get_db
        db = get_db()
        
        # Chercher l'utilisateur (par username ou email)
        user = db.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?',
            (username, username)
        ).fetchone()
        
        if not user:
            return False, "Nom d'utilisateur ou mot de passe incorrect", {}
        
        # Vérifier le mot de passe
        if not check_password_hash(user['password_hash'], password):
            return False, "Nom d'utilisateur ou mot de passe incorrect", {}
        
        # Mettre à jour la dernière connexion
        db.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (datetime.now().isoformat(), user['id'])
        )
        db.commit()
        
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'is_admin': user['is_admin']
        }
        
        logger.info(f"Utilisateur connecté : {username}")
        return True, "Connexion réussie", user_data
        
    except Exception as e:
        logger.error(f"Erreur authentification : {e}")
        return False, f"Erreur lors de la connexion : {str(e)}", {}


def get_current_user():
    """
    Récupère les informations de l'utilisateur actuellement connecté.
    
    Returns:
        dict ou None
    """
    if 'user_id' not in session:
        return None
    
    try:
        from tracker.database import get_db
        db = get_db()
        
        user = db.execute(
            'SELECT id, username, email, is_admin, created_at, last_login FROM users WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        
        if user:
            return dict(user)
        return None
        
    except Exception as e:
        logger.error(f"Erreur récupération utilisateur : {e}")
        return None


def logout_user():
    """
    Déconnecte l'utilisateur actuel.
    """
    if 'user_id' in session:
        logger.info(f"Utilisateur déconnecté : {session.get('username', 'Unknown')}")
        session.clear()


def init_auth_db(db):
    """
    Initialise les tables d'authentification dans la base de données.
    
    Args:
        db: Connexion à la base de données
    """
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Créer un compte admin par défaut si aucun utilisateur n'existe
    existing_users = db.execute('SELECT COUNT(*) as count FROM users').fetchone()
    
    if existing_users['count'] == 0:
        admin_password = generate_password_hash('admin123')
        db.execute(
            '''INSERT INTO users (username, email, password_hash, is_admin, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            ('admin', 'admin@p2p.local', admin_password, 1, datetime.now().isoformat())
        )
        db.commit()
        logger.info("Compte administrateur par défaut créé : admin / admin123")
