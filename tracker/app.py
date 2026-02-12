"""
Point d'entrée principal du tracker.
Lance le serveur Flask et configure les tâches planifiées.
"""

import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from tracker import create_app, db
from tracker.database import init_database
from tracker.routes import api_bp, web_bp, auth_bp
from tracker.models import Peer, User
from shared.constants import PEER_STATUS_OFFLINE

logger = logging.getLogger(__name__)


def cleanup_inactive_peers(app):
    """
    Tâche planifiée : Marque les peers inactifs comme hors ligne.
    
    Args:
        app: Instance de l'application Flask
    """
    with app.app_context():
        try:
            config = app.config['APP_CONFIG']
            timeout = config['tracker']['heartbeat']['timeout']
            
            # Calculer la date limite
            cutoff_time = datetime.utcnow() - timedelta(seconds=timeout)
            
            # Trouver les peers inactifs
            inactive_peers = Peer.query.filter(
                Peer.last_heartbeat < cutoff_time,
                Peer.status != PEER_STATUS_OFFLINE
            ).all()
            
            # Marquer comme hors ligne
            count = 0
            for peer in inactive_peers:
                peer.status = PEER_STATUS_OFFLINE
                count += 1
            
            if count > 0:
                db.session.commit()
                logger.info(f"{count} peer(s) marqué(s) comme hors ligne")
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des peers inactifs: {e}")
            db.session.rollback()


def main():
    """
    Fonction principale pour lancer le tracker.
    """
    # Créer l'application
    app = create_app()
    
    # Enregistrer les blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    
    # Initialiser la base de données
    init_database(app)
    
    # Appliquer les migrations automatiques
    from tracker.migrations import apply_all_migrations
    with app.app_context():
        apply_all_migrations(app)
    
    # Créer le compte admin par défaut
    with app.app_context():
        if User.create_admin_if_not_exists():
            logger.info("✅ Compte administrateur créé : admin / admin123")
    
    # Configurer le scheduler pour les tâches planifiées
    scheduler = BackgroundScheduler()
    
    # Tâche : Nettoyage des peers inactifs toutes les 30 secondes
    scheduler.add_job(
        func=lambda: cleanup_inactive_peers(app),
        trigger='interval',
        seconds=30,
        id='cleanup_peers',
        name='Nettoyage des peers inactifs'
    )
    
    scheduler.start()
    logger.info("Scheduler démarré : nettoyage des peers inactifs toutes les 30s")
    
    # Récupérer la configuration
    config = app.config['APP_CONFIG']
    tracker_config = config['tracker']
    
    # Utiliser le port de Railway si disponible (variable d'environnement PORT)
    # Sinon utiliser le port de la configuration
    host = tracker_config['host']
    port = int(os.environ.get('PORT', tracker_config['port']))
    
    logger.info("=" * 60)
    logger.info("🚀 Démarrage du Tracker P2P")
    logger.info("=" * 60)
    logger.info(f"📍 URL: http://{host}:{port}")
    logger.info(f"📊 Dashboard: http://localhost:{port}/")
    logger.info(f"📈 Statistiques: http://localhost:{port}/statistics")
    logger.info(f"🔌 API: http://localhost:{port}/api/")
    logger.info("=" * 60)
    
    try:
        # Lancer le serveur Flask
        app.run(
            host=host,
            port=port,
            debug=False,  # Mettre True pour le développement
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Arrêt du tracker...")
        scheduler.shutdown()
        logger.info("✅ Tracker arrêté proprement")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        scheduler.shutdown()
        raise


if __name__ == '__main__':
    main()