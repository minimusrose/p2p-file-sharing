"""
Routes API et web pour le tracker.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, current_app, session, redirect, url_for, flash
from sqlalchemy import or_, func

from tracker import db
from tracker.models import Peer, File, Download, Statistics, User
from shared.constants import (
    PEER_STATUS_ONLINE, PEER_STATUS_OFFLINE,
    DOWNLOAD_STATUS_COMPLETED, DOWNLOAD_STATUS_FAILED,
    SUCCESS_REGISTERED, ERROR_TRACKER_UNAVAILABLE
)
from shared.utils import generate_unique_id

logger = logging.getLogger(__name__)

# Blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api')
web_bp = Blueprint('web', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ==================== AUTHENTICATION HELPER ====================

def login_required(f):
    """Décorateur pour protéger les routes nécessitant une authentification"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.landing'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== ROUTES API ====================

@api_bp.route('/register', methods=['POST'])
def register_peer():
    """
    Enregistre un nouveau peer sur le tracker.
    
    Body JSON:
        - peer_id: ID unique du peer
        - name: Nom du peer
        - ip_address: Adresse IP
        - port: Port du serveur peer
        
    Returns:
        JSON avec le statut de l'enregistrement
    """
    try:
        data = request.get_json()
        
        # Validation
        required_fields = ['peer_id', 'name', 'ip_address', 'port']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Champs manquants'}), 400
        
        # Vérifier si le peer existe déjà (par ID)
        existing_peer = Peer.query.filter_by(id=data['peer_id']).first()
        
        if existing_peer:
            # Mettre à jour le peer existant
            existing_peer.name = data['name']
            existing_peer.ip_address = data['ip_address']
            existing_peer.port = data['port']
            existing_peer.status = PEER_STATUS_ONLINE
            existing_peer.update_heartbeat()
            logger.info(f"Peer réenregistré: {existing_peer.name} ({data['peer_id'][:8]}...)")
        else:
            # Avant de créer un nouveau peer, supprimer uniquement les anciens enregistrements
            # avec le même peer_id (anciennes sessions du même peer)
            # NE PAS supprimer les autres peers avec le même nom/IP (cas de tests avec plusieurs peers sur même machine)
            old_peers = Peer.query.filter_by(
                id=data['peer_id']
            ).all()
            
            if old_peers:
                logger.info(f"Nettoyage de {len(old_peers)} ancien(s) enregistrement(s) pour peer_id {data['peer_id'][:8]}...")
                for old_peer in old_peers:
                    # Supprimer aussi les fichiers associés
                    File.query.filter_by(owner_id=old_peer.id).delete()
                    db.session.delete(old_peer)
            
            # Créer un nouveau peer
            new_peer = Peer(
                id=data['peer_id'],
                name=data['name'],
                ip_address=data['ip_address'],
                port=data['port'],
                status=PEER_STATUS_ONLINE
            )
            db.session.add(new_peer)
            
            # Mettre à jour les statistiques
            stats = Statistics.get_or_create()
            stats.total_peers_registered += 1
            
            logger.info(f"Nouveau peer enregistré: {new_peer.name} ({data['peer_id'][:8]}...)")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': SUCCESS_REGISTERED,
            'peer_id': data['peer_id']
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du peer: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    Reçoit un heartbeat d'un peer pour signaler sa présence.
    
    Body JSON:
        - peer_id: ID du peer
        
    Returns:
        JSON avec confirmation
    """
    try:
        data = request.get_json()
        peer_id = data.get('peer_id')
        
        if not peer_id:
            return jsonify({'error': 'peer_id manquant'}), 400
        
        peer = Peer.query.filter_by(id=peer_id).first()
        
        if not peer:
            return jsonify({'error': 'Peer non trouvé'}), 404
        
        peer.update_heartbeat()
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Erreur lors du heartbeat: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/unregister', methods=['POST'])
def unregister_peer():
    """
    Désenregistre un peer du tracker.
    
    Body JSON:
        - peer_id: ID du peer
        
    Returns:
        JSON avec confirmation
    """
    try:
        data = request.get_json()
        peer_id = data.get('peer_id')
        
        if not peer_id:
            return jsonify({'error': 'peer_id manquant'}), 400
        
        peer = Peer.query.filter_by(id=peer_id).first()
        
        if not peer:
            return jsonify({'error': 'Peer non trouvé'}), 404
        
        peer.status = PEER_STATUS_OFFLINE
        db.session.commit()
        
        logger.info(f"Peer déconnecté: {peer.name}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Erreur lors du désenregistrement: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/announce_files', methods=['POST'])
def announce_files():
    """
    Un peer annonce les fichiers qu'il partage.
    
    Body JSON:
        - peer_id: ID du peer
        - files: Liste de fichiers [{name, size, hash, is_chunked, ...}]
        
    Returns:
        JSON avec confirmation
    """
    try:
        data = request.get_json()
        peer_id = data.get('peer_id')
        files_data = data.get('files', [])
        
        if not peer_id:
            return jsonify({'error': 'peer_id manquant'}), 400
        
        peer = Peer.query.filter_by(id=peer_id).first()
        
        if not peer:
            return jsonify({'error': 'Peer non trouvé'}), 404
        
        # Supprimer les anciens fichiers de ce peer
        File.query.filter_by(owner_id=peer_id).delete()
        
        # Ajouter les nouveaux fichiers
        files_added = 0
        for file_data in files_data:
            import json
            
            # Gérer allowed_peers
            allowed_peers_json = None
            is_private = file_data.get('is_private', False)
            if is_private and file_data.get('allowed_peers'):
                allowed_peers_json = json.dumps(file_data['allowed_peers'])
            
            new_file = File(
                id=file_data.get('id', generate_unique_id()),
                name=file_data['name'],
                size=file_data['size'],
                hash=file_data['hash'],
                is_chunked=file_data.get('is_chunked', False),
                chunk_size=file_data.get('chunk_size'),
                chunks_count=file_data.get('chunks_count'),
                chunks_hashes=file_data.get('chunks_hashes'),
                owner_id=peer_id,
                is_private=is_private,
                allowed_peers=allowed_peers_json
            )
            db.session.add(new_file)
            files_added += 1
        
        # Mettre à jour les statistiques
        stats = Statistics.get_or_create()
        stats.total_files_shared = File.query.count()
        
        db.session.commit()
        
        logger.info(f"Peer {peer.name} a annoncé {files_added} fichiers")
        
        return jsonify({
            'success': True,
            'files_added': files_added
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de l'annonce de fichiers: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/search', methods=['GET'])
def search_files():
    """
    Recherche des fichiers par nom.
    
    Query params:
        - q: Terme de recherche
        - limit: Nombre max de résultats (défaut: 50)
        - peer_id: ID du peer qui fait la recherche (pour filtrer les fichiers privés)
        
    Returns:
        JSON avec la liste des fichiers trouvés
    """
    try:
        import json
        
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 50))
        requesting_peer_id = request.args.get('peer_id')  # ID du peer qui cherche
        
        if not query:
            # Retourner tous les fichiers si pas de recherche
            files = File.query.limit(limit).all()
        else:
            # Recherche par nom (insensible à la casse)
            files = File.query.filter(
                File.name.ilike(f'%{query}%')
            ).limit(limit).all()
        
        results = []
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        for file in files:
            # Vérifier les permissions d'accès
            if file.is_private and file.allowed_peers:
                # Fichier privé : vérifier si le peer a le droit
                try:
                    allowed_list = json.loads(file.allowed_peers)
                    if requesting_peer_id not in allowed_list and file.owner_id != requesting_peer_id:
                        # Peer non autorisé : ne pas inclure ce fichier
                        continue
                except:
                    # Erreur de parsing : considérer comme public
                    pass
            
            file_dict = file.to_dict()
            # Ajouter l'info de disponibilité
            file_dict['owner_online'] = file.owner.is_online(timeout)
            results.append(file_dict)
        
        return jsonify({
            'success': True,
            'count': len(results),
            'files': results
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/peers', methods=['GET'])
def get_peers():
    """
    Récupère la liste de tous les peers.
    
    Query params:
        - status: Filtrer par statut (online, offline)
        
    Returns:
        JSON avec la liste des peers
    """
    try:
        status_filter = request.args.get('status')
        
        query = Peer.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        peers = query.all()
        
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        peers_list = []
        for peer in peers:
            peer_dict = peer.to_dict()
            peer_dict['is_online'] = peer.is_online(timeout)
            peers_list.append(peer_dict)
        
        return jsonify({
            'success': True,
            'count': len(peers_list),
            'peers': peers_list
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des peers: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/file/<file_id>/permissions', methods=['POST'])
def update_file_permissions(file_id):
    """
    Met à jour les permissions d'accès d'un fichier.
    
    Args:
        file_id: ID du fichier
    
    Body JSON:
        - peer_id: ID du peer propriétaire (obligatoire)
        - is_private: true pour activer le partage sélectif, false pour public
        - allowed_peers: liste des peer_id autorisés (si is_private=true)
        
    Returns:
        JSON avec confirmation
    """
    try:
        import json
        
        data = request.get_json()
        
        peer_id = data.get('peer_id')
        is_private = data.get('is_private', False)
        allowed_peers = data.get('allowed_peers', [])
        
        if not peer_id:
            return jsonify({'error': 'peer_id manquant'}), 400
        
        # Récupérer le fichier
        file = File.query.filter_by(id=file_id).first()
        
        if not file:
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        # Vérifier que le peer est bien le propriétaire
        if file.owner_id != peer_id:
            return jsonify({'error': 'Accès refusé : vous n\'êtes pas le propriétaire'}), 403
        
        # Mettre à jour les permissions
        file.is_private = is_private
        if is_private and allowed_peers:
            file.allowed_peers = json.dumps(allowed_peers)
        else:
            file.allowed_peers = None
        
        db.session.commit()
        
        logger.info(f"Permissions mises à jour pour {file.name} : is_private={is_private}, allowed_peers={allowed_peers}")
        
        return jsonify({
            'success': True,
            'message': 'Permissions mises à jour',
            'file': file.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur mise à jour permissions : {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/file/<file_id>/peers', methods=['GET'])
def get_file_peers(file_id):
    """
    Récupère les peers qui possèdent un fichier spécifique.
    
    Returns:
        JSON avec la liste des peers possédant le fichier
    """
    try:
        file = File.query.filter_by(id=file_id).first()
        
        if not file:
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        # Pour l'instant, un fichier n'a qu'un propriétaire
        # Dans le futur, on pourrait gérer plusieurs copies
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        owner_dict = file.owner.to_dict()
        owner_dict['is_online'] = file.owner.is_online(timeout)
        
        return jsonify({
            'success': True,
            'file': file.to_dict(),
            'peers': [owner_dict]
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des peers du fichier: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    Récupère les statistiques globales du système.
    
    Returns:
        JSON avec les statistiques
    """
    try:
        stats = Statistics.get_or_create()
        
        # Statistiques en temps réel
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        online_peers = sum(1 for peer in Peer.query.all() if peer.is_online(timeout))
        total_peers = Peer.query.count()
        total_files = File.query.count()
        
        # Fichiers les plus téléchargés
        top_files = File.query.order_by(File.download_count.desc()).limit(10).all()
        
        # Téléchargements récents
        recent_downloads = Download.query.order_by(Download.started_at.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'statistics': stats.to_dict(),
            'realtime': {
                'online_peers': online_peers,
                'total_peers': total_peers,
                'total_files': total_files
            },
            'top_files': [f.to_dict() for f in top_files],
            'recent_downloads': [d.to_dict() for d in recent_downloads]
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/log_download', methods=['POST'])
def log_download():
    """
    Enregistre un téléchargement dans l'historique.
    
    Body JSON:
        - file_id: ID du fichier
        - source_peer_id: ID du peer source
        - destination_peer_id: ID du peer destination
        - status: Statut (completed, failed)
        - bytes_transferred: Octets transférés
        
    Returns:
        JSON avec confirmation
    """
    try:
        data = request.get_json()
        
        download = Download(
            id=generate_unique_id(),
            file_id=data['file_id'],
            source_peer_id=data['source_peer_id'],
            destination_peer_id=data['destination_peer_id'],
            status=data.get('status', DOWNLOAD_STATUS_COMPLETED),
            bytes_transferred=data.get('bytes_transferred', 0),
            completed_at=datetime.utcnow() if data.get('status') == DOWNLOAD_STATUS_COMPLETED else None
        )
        
        db.session.add(download)
        
        # Incrémenter le compteur de téléchargements du fichier
        if data.get('status') == DOWNLOAD_STATUS_COMPLETED:
            file = File.query.filter_by(id=data['file_id']).first()
            if file:
                file.increment_download_count()
            
            # Mettre à jour les statistiques globales
            stats = Statistics.get_or_create()
            stats.total_downloads += 1
            stats.total_bytes_transferred += data.get('bytes_transferred', 0)
        
        db.session.commit()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du téléchargement: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== ROUTES WEB ====================

@web_bp.route('/')
def landing():
    """
    Page d'accueil publique - Landing page.
    """
    # Si l'utilisateur est déjà connecté, rediriger vers le dashboard
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))
    
    return render_template('landing.html')


@web_bp.route('/dashboard')
def dashboard():
    """
    Dashboard du tracker (nécessite authentification).
    """
    # Vérifier si l'utilisateur est connecté
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder au dashboard.', 'warning')
        return redirect(url_for('web.landing'))
    
    try:
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        # Récupérer les données
        peers = Peer.query.all()
        files = File.query.order_by(File.shared_at.desc()).limit(50).all()
        
        # Calculer les stats en temps réel
        online_peers = [p for p in peers if p.is_online(timeout)]
        
        # Enrichir les fichiers avec info de disponibilité
        files_data = []
        for file in files:
            file_dict = file.to_dict()
            file_dict['owner_online'] = file.owner.is_online(timeout)
            files_data.append(file_dict)
        
        return render_template('dashboard.html',
                             peers=peers,
                             online_peers=online_peers,
                             files=files_data,
                             timeout=timeout)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement du dashboard: {e}")
        return f"Erreur: {e}", 500


@web_bp.route('/files')
def files():
    """
    Page de gestion des fichiers (nécessite authentification).
    """
    # Vérifier si l'utilisateur est connecté
    if 'user_id' not in session:
        flash('Veuillez vous connecter pour accéder aux fichiers.', 'warning')
        return redirect(url_for('web.landing'))
    
    try:
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        # Récupérer tous les fichiers avec leurs propriétaires (relations chargées)
        files = File.query.order_by(File.shared_at.desc()).all()
        
        # Récupérer tous les peers
        peers = Peer.query.all()
        
        # Compter les peers en ligne
        online_peers_count = sum(1 for p in peers if p.is_online(timeout))
        
        # Passer directement les objets (pas de to_dict())
        # Le template peut accéder aux relations
        return render_template('files.html',
                             files=files,
                             peers=peers,
                             timeout=timeout,
                             online_peers_count=online_peers_count)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des fichiers: {e}", exc_info=True)
        return f"Erreur: {e}", 500


@web_bp.route('/statistics')
def statistics():
    """
    Page de statistiques détaillées.
    """
    try:
        stats = Statistics.get_or_create()
        
        # Statistiques en temps réel
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        peers = Peer.query.all()
        online_peers = [p for p in peers if p.is_online(timeout)]
        
        # Fichiers les plus téléchargés
        top_files = File.query.order_by(File.download_count.desc()).limit(10).all()
        
        # Téléchargements récents
        recent_downloads = Download.query.order_by(Download.started_at.desc()).limit(20).all()
        
        # Activité par jour (derniers 7 jours)
        # TODO: Implémenter les graphiques d'activité
        
        return render_template('statistics.html',
                             stats=stats,
                             online_peers_count=len(online_peers),
                             total_peers_count=len(peers),
                             top_files=top_files,
                             recent_downloads=recent_downloads)
        
    except Exception as e:
        logger.error(f"Erreur lors du chargement des statistiques: {e}")
        return f"Erreur: {e}", 500


# ==================== ROUTES D'AUTHENTIFICATION ====================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Page et traitement de connexion.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Veuillez remplir tous les champs.', 'danger')
            return redirect(url_for('web.landing'))
        
        # Chercher l'utilisateur
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.check_password(password):
            # Vérifier si le compte est actif
            if not user.is_active:
                flash('Votre compte est désactivé.', 'danger')
                return redirect(url_for('web.landing'))
            
            # Créer la session
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            # Mettre à jour last_login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Bienvenue {user.username} !', 'success')
            logger.info(f"Utilisateur connecté : {user.username}")
            
            return redirect(url_for('web.dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
            return redirect(url_for('web.landing'))
    
    # GET : rediriger vers landing
    return redirect(url_for('web.landing'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Page et traitement d'inscription.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Validation
        if not all([username, email, password, password_confirm]):
            flash('Veuillez remplir tous les champs.', 'danger')
            return redirect(url_for('web.landing'))
        
        if len(username) < 3:
            flash('Le nom d\'utilisateur doit contenir au moins 3 caractères.', 'danger')
            return redirect(url_for('web.landing'))
        
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return redirect(url_for('web.landing'))
        
        if password != password_confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return redirect(url_for('web.landing'))
        
        # Vérifier si l'utilisateur existe
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            flash('Ce nom d\'utilisateur ou email est déjà utilisé.', 'danger')
            return redirect(url_for('web.landing'))
        
        try:
            # Créer l'utilisateur
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Compte créé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
            logger.info(f"Nouvel utilisateur créé : {username}")
            
            # Connexion automatique
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            return redirect(url_for('web.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur création utilisateur : {e}")
            flash('Erreur lors de la création du compte.', 'danger')
            return redirect(url_for('web.landing'))
    
    # GET : rediriger vers landing
    return redirect(url_for('web.landing'))


@auth_bp.route('/logout')
def logout():
    """
    Déconnexion de l'utilisateur.
    """
    username = session.get('username', 'Unknown')
    session.clear()
    flash('Vous êtes déconnecté.', 'info')
    logger.info(f"Utilisateur déconnecté : {username}")
    return redirect(url_for('web.landing'))


# ==================== ROUTES DE GESTION DES FICHIERS ====================

@web_bp.route('/files/download/<file_id>')
@login_required
def download_file(file_id):
    """Proxy de téléchargement depuis le peer"""
    from tracker.models import File, Peer
    import requests
    from flask import Response, stream_with_context
    
    file = File.query.get(file_id)
    if not file:
        return jsonify({'success': False, 'error': 'Fichier introuvable'}), 404
    
    peer = Peer.query.get(file.peer_id)
    if not peer or not peer.is_online():
        return jsonify({'success': False, 'error': 'Peer hors ligne'}), 503
    
    try:
        # Télécharger depuis le peer
        peer_url = f"http://{peer.ip_address}:{peer.port}/api/files/{file_id}/download"
        
        response = requests.get(peer_url, stream=True, timeout=30)
        
        if response.status_code == 200:
            # Streamer le fichier
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            return Response(
                stream_with_context(generate()),
                headers={
                    'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                    'Content-Disposition': f'attachment; filename="{file.name}"',
                    'Content-Length': response.headers.get('Content-Length', '')
                }
            )
        else:
            return jsonify({'success': False, 'error': f'Erreur peer: {response.status_code}'}), 502
            
    except Exception as e:
        print(f"❌ Erreur téléchargement: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@web_bp.route('/api/my-uploaded-files')
@login_required
def my_uploaded_files():
    """API pour récupérer les fichiers uploadés par l'utilisateur connecté"""
    try:
        user_id = session.get('user_id')
        uploaded_files_session = session.get('uploaded_files', [])
        
        # Chercher les fichiers correspondants
        my_files = []
        for upload_info in uploaded_files_session:
            # Chercher le fichier par nom et peer_id
            files = File.query.filter_by(
                name=upload_info['filename'],
                owner_id=upload_info['peer_id']
            ).all()
            
            for file in files:
                my_files.append({
                    'id': file.id,
                    'name': file.name,
                    'size': file.size,
                    'shared_at': file.shared_at.isoformat() if file.shared_at else None,
                    'peer_name': file.owner.name if file.owner else 'Unknown',
                    'is_online': file.owner.is_online() if file.owner else False,
                    'uploaded_at': upload_info['timestamp']
                })
        
        return jsonify({
            'success': True,
            'files': my_files,
            'count': len(my_files)
        })
        
    except Exception as e:
        logger.error(f"Erreur récupération fichiers utilisateur: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@web_bp.route('/files/upload', methods=['POST'])
def upload_file():
    """
    Upload d'un fichier via l'interface web.
    Le fichier est stocké temporairement puis transféré à un peer.
    """
    # Vérifier authentification
    if 'user_id' not in session:
        return jsonify({
            'success': False,
            'error': 'Non authentifié'
        }), 401
    
    try:
        import os
        import tempfile
        from werkzeug.utils import secure_filename
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Nom de fichier vide'
            }), 400
        
        # Vérifier la taille (100 MB max pour le mode web)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 100 * 1024 * 1024  # 100 MB
        if file_size > max_size:
            return jsonify({
                'success': False,
                'error': f'Fichier trop volumineux ({file_size / 1024 / 1024:.2f} MB). Maximum : 100 MB en mode web.'
            }), 400
        
        # Sauvegarder temporairement
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        # Trouver un peer en ligne pour stocker le fichier
        config = current_app.config['APP_CONFIG']
        timeout = config['tracker']['heartbeat']['timeout']
        
        online_peers = [p for p in Peer.query.all() if p.is_online(timeout)]
        
        if not online_peers:
            # Aucun peer disponible - proposer de télécharger l'app
            os.remove(temp_path)
            return jsonify({
                'success': False,
                'error': 'no_peer_available',
                'message': 'Aucun peer disponible pour stocker le fichier. Téléchargez l\'application desktop pour partager vos fichiers !'
            }), 503
        
        # Choisir le peer avec le moins de fichiers
        target_peer = min(online_peers, key=lambda p: len(p.files))
        
        logger.info(f"Upload de {filename} vers peer {target_peer.name} (port {target_peer.port})")
        
        # Envoyer le fichier au peer via son API
        import requests
        
        peer_url = f"http://{target_peer.ip_address}:{target_peer.port}/api/files/upload"
        
        with open(temp_path, 'rb') as f:
            files_data = {'files': (filename, f, 'application/octet-stream')}
            response = requests.post(peer_url, files=files_data, timeout=60)
        
        # Nettoyer le fichier temporaire
        os.remove(temp_path)
        
        if response.status_code == 200:
            # Marquer le fichier comme uploadé par cet utilisateur
            # Attendre que le peer annonce le fichier, puis le mettre à jour
            # Pour l'instant, on retourne juste le succès
            
            logger.info(f"Fichier {filename} uploadé avec succès vers peer {target_peer.name} par user {session.get('username')}")
            
            # Enregistrer dans une session temporaire pour attribution ultérieure
            if 'uploaded_files' not in session:
                session['uploaded_files'] = []
            session['uploaded_files'].append({
                'filename': filename,
                'peer_id': target_peer.id,
                'user_id': session['user_id'],
                'timestamp': datetime.utcnow().isoformat()
            })
            session.modified = True
            
            return jsonify({
                'success': True,
                'message': f'Fichier partagé sur le peer {target_peer.name}',
                'peer': target_peer.name,
                'filename': filename
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Erreur lors de l\'envoi au peer : {response.status_code}'
            }), 500
        
    except Exception as e:
        logger.error(f"Erreur upload fichier : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== ROUTES DE TÉLÉCHARGEMENT ====================

@web_bp.route('/download')
def download_page():
    """Page de téléchargement des applications desktop"""
    return render_template('download.html')


@web_bp.route('/download/linux')
def download_linux():
    """Téléchargement du script d'installation Linux"""
    from flask import send_file
    import os
    
    script_path = os.path.join(current_app.root_path, '..', 'run_p2p_linux.sh')
    
    if os.path.exists(script_path):
        return send_file(
            script_path,
            as_attachment=True,
            download_name='run_p2p_linux.sh',
            mimetype='application/x-sh'
        )
    else:
        return jsonify({
            'success': False,
            'error': 'Fichier non trouvé'
        }), 404


@web_bp.route('/download/windows')
def download_windows():
    """Téléchargement du script d'installation Windows"""
    from flask import send_file
    import os
    
    script_path = os.path.join(current_app.root_path, '..', 'run_p2p_windows.bat')
    
    if os.path.exists(script_path):
        return send_file(
            script_path,
            as_attachment=True,
            download_name='run_p2p_windows.bat',
            mimetype='application/x-bat'
        )
    else:
        return jsonify({
            'success': False,
            'error': 'Fichier non trouvé'
        }), 404