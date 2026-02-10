"""
Routes Flask pour l'interface web du peer.
"""

import logging
from flask import Blueprint, render_template, request, jsonify, send_file
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Créer le blueprint
peer_bp = Blueprint('peer', __name__)

# Instance globale de l'application peer (sera injectée)
_peer_app = None


def init_routes(peer_app):
    """
    Initialise les routes avec l'instance de PeerApplication.
    
    Args:
        peer_app: Instance de PeerApplication
    """
    global _peer_app
    _peer_app = peer_app


@peer_bp.route('/')
def index():
    """
    Page Dashboard - Vue d'ensemble.
    """
    try:
        # Vérifier que _peer_app est initialisé
        if _peer_app is None:
            return "Peer application not initialized", 500
            
        return render_template('dashboard.html')
        
    except Exception as e:
        logger.error(f"Erreur page dashboard : {e}", exc_info=True)
        return render_template('dashboard.html', error=str(e))


@peer_bp.route('/my-files')
def my_files():
    """
    Page Mes Fichiers - Gestion des fichiers partagés.
    """
    try:
        return render_template('my_files.html')
        
    except Exception as e:
        logger.error(f"Erreur page mes fichiers : {e}", exc_info=True)
        return f"Erreur : {str(e)}", 500


@peer_bp.route('/network')
def network():
    """
    Page Réseau - Recherche et téléchargement.
    """
    try:
        return render_template('network.html')
        
    except Exception as e:
        logger.error(f"Erreur page réseau : {e}", exc_info=True)
        return f"Erreur : {str(e)}", 500


# Routes compatibilité (anciennes URLs)
@peer_bp.route('/files')
def files():
    """Redirection vers mes fichiers."""
    from flask import redirect, url_for
    return redirect(url_for('peer.my_files'))


@peer_bp.route('/downloads')
def downloads():
    """
    Page de gestion des téléchargements.
    """
    try:
        # Récupérer tous les téléchargements
        download_jobs = _peer_app.peer_client.get_all_downloads()
        
        return render_template('downloads.html', downloads=download_jobs)
        
    except Exception as e:
        logger.error(f"Erreur page téléchargements : {e}")
        return render_template('downloads.html', downloads=[], error=str(e))


@peer_bp.route('/settings')
def settings():
    """
    Page des paramètres.
    """
    try:
        config = _peer_app.config
        
        return render_template('settings.html', config=config)
        
    except Exception as e:
        logger.error(f"Erreur page paramètres : {e}")
        return render_template('settings.html', config={}, error=str(e))


# ========== API ENDPOINTS ==========

@peer_bp.route('/api/files/local')
def api_local_files():
    """
    API : Liste des fichiers locaux partagés.
    """
    try:
        files = _peer_app.file_scanner.get_files()
        
        return jsonify({
            'success': True,
            'files': [f.to_dict() for f in files]
        })
        
    except Exception as e:
        logger.error(f"Erreur API local files : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/files/scan', methods=['POST'])
def api_scan_files():
    """
    API : Lance un scan des fichiers partagés.
    Retourne les nouveaux fichiers détectés pour configuration des permissions.
    """
    try:
        # Sauvegarder l'index avant le scan pour détecter les nouveaux
        old_file_ids = set(_peer_app.file_scanner.files_index.keys())
        
        # Scanner
        files = _peer_app.file_scanner.scan_files()
        
        # Détecter les nouveaux fichiers (pas dans l'ancien index)
        new_file_ids = set(_peer_app.file_scanner.files_index.keys()) - old_file_ids
        new_files = [f.to_dict() for f in files if f.id in new_file_ids]
        
        # NE PAS synchroniser avec le tracker tout de suite
        # La synchronisation se fera après la configuration des permissions
        
        return jsonify({
            'success': True,
            'message': f'{len(files)} fichiers scannés',
            'files_count': len(files),
            'new_files_count': len(new_files),
            'new_files': new_files  # Liste des nouveaux fichiers à configurer
        })
        
    except Exception as e:
        logger.error(f"Erreur API scan : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/files/upload', methods=['POST'])
def api_upload_files():
    """
    API : Upload de fichiers vers le dossier de partage.
    Gère automatiquement la fragmentation distribuée pour fichiers ≥ 1GB.
    """
    try:
        import shutil
        from werkzeug.utils import secure_filename
        import json
        
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni'
            }), 400
        
        files = request.files.getlist('files')
        uploaded_count = 0
        distributed_count = 0
        shared_folder = Path(_peer_app.config['peer']['shared_folder'])
        
        # Créer le dossier s'il n'existe pas
        shared_folder.mkdir(parents=True, exist_ok=True)
        
        results = []
        
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = shared_folder / filename
                
                # Sauvegarder le fichier temporairement pour connaître sa taille
                file.save(str(filepath))
                file_size = filepath.stat().st_size
                
                logger.info(f"Fichier uploadé : {filename} ({file_size / 1024 / 1024:.2f} MB)")
                
                # Vérifier si le fichier doit être distribué
                if _peer_app.distributed_chunk_manager.should_distribute(file_size):
                    # Vérifier la disponibilité des peers
                    can_dist, message = _peer_app.distributed_chunk_manager.can_distribute(file_size)
                    
                    if not can_dist:
                        # Supprimer le fichier car distribution impossible
                        filepath.unlink()
                        return jsonify({
                            'success': False,
                            'error': 'distribution_required',
                            'message': message,
                            'file_size_gb': file_size / 1024 / 1024 / 1024,
                            'available_peers': len(_peer_app.distributed_chunk_manager.get_available_peers())
                        }), 400
                    
                    # Distribuer le fichier
                    logger.info(f"Distribution du fichier {filename} ({file_size / 1024 / 1024 / 1024:.2f} GB)")
                    
                    # Scanner et obtenir le FileInfo
                    _peer_app.file_scanner.scan_files()
                    file_info = next(
                        (f for f in _peer_app.cache_manager.get_all_files() if f.name == filename),
                        None
                    )
                    
                    if file_info:
                        # Calculer les hashes des chunks
                        chunks_hashes = _peer_app.chunk_manager.calculate_chunks_hashes(filepath)
                        
                        # Distribuer
                        distribution_map = _peer_app.distributed_chunk_manager.distribute_chunks(
                            file_info, filepath, chunks_hashes
                        )
                        
                        # Mettre à jour les métadonnées du fichier
                        file_info.is_chunked = True
                        file_info.is_distributed = True
                        file_info.chunk_size = _peer_app.config['chunking']['chunk_size']
                        file_info.chunks_count = len(chunks_hashes)
                        file_info.chunks_hashes = json.dumps(chunks_hashes)
                        file_info.distribution_map = json.dumps({str(k): v for k, v in distribution_map.items()})
                        
                        # Sauvegarder dans le cache
                        _peer_app.cache_manager.add_file(file_info)
                        
                        distributed_count += 1
                        
                        # Résumé de la distribution
                        summary = _peer_app.distributed_chunk_manager.get_chunk_distribution_summary(distribution_map)
                        results.append({
                            'filename': filename,
                            'size': file_size,
                            'distributed': True,
                            'chunks_count': len(chunks_hashes),
                            'distribution_summary': {
                                peer_id: len(chunks) 
                                for peer_id, chunks in summary.items()
                            }
                        })
                    else:
                        logger.warning(f"FileInfo introuvable pour {filename}")
                        results.append({
                            'filename': filename,
                            'size': file_size,
                            'distributed': False,
                            'error': 'Métadonnées introuvables'
                        })
                else:
                    # Fichier < 1GB, upload normal
                    uploaded_count += 1
                    results.append({
                        'filename': filename,
                        'size': file_size,
                        'distributed': False
                    })
        
        # Scanner automatiquement après upload
        _peer_app.file_scanner.scan_files()
        
        # Synchroniser avec le tracker (gérer les erreurs silencieusement)
        if _peer_app.tracker_connected:
            try:
                _peer_app.sync_files_with_tracker()
            except Exception as sync_error:
                logger.warning(f"Erreur sync tracker après upload (non bloquant): {sync_error}")
        
        return jsonify({
            'success': True,
            'files_count': uploaded_count + distributed_count,
            'uploaded_count': uploaded_count,
            'distributed_count': distributed_count,
            'message': f'{uploaded_count} fichier(s) uploadé(s), {distributed_count} distribué(s)',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Erreur API upload : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/peer/info')
def api_peer_info():
    """
    API : Informations sur ce peer.
    """
    try:
        return jsonify({
            'success': True,
            'id': _peer_app.peer_id,
            'name': _peer_app.config.get('peer', {}).get('name', 'Peer'),
            'port': _peer_app.config.get('peer', {}).get('port', 0)
        })
    except Exception as e:
        logger.error(f"Erreur API peer info : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/activity/recent')
def api_recent_activity():
    """
    API : Activité récente (uploads/downloads).
    """
    try:
        # Pour l'instant, retourner une liste vide
        # TODO: Implémenter un système de logging des activités
        return jsonify({
            'success': True,
            'activities': []
        })
    except Exception as e:
        logger.error(f"Erreur API activity : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/files/search')
def api_search_files():
    """
    API : Recherche de fichiers.
    """
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 50, type=int)
        only_online = request.args.get('only_online', 'true').lower() == 'true'
        
        # Rechercher (query vide = tous les fichiers)
        results = _peer_app.search_files(query, limit, only_online)
        
        return jsonify({
            'success': True,
            'results': [f.to_dict() for f in results],
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Erreur API search : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/download/start', methods=['POST'])
def api_start_download():
    """
    API : Démarre un téléchargement.
    """
    try:
        data = request.get_json(force=True)
        
        if not data:
            logger.error("Aucune donnée JSON reçue")
            return jsonify({
                'success': False,
                'error': 'Aucune donnée reçue'
            }), 400
        
        file_id = data.get('file_id')
        peer_id = data.get('peer_id')
        force_download = data.get('force_download', False)  # Nouveau paramètre
        
        logger.info(f"Demande de téléchargement : file_id={file_id}, peer_id={peer_id}, force={force_download}")
        
        if not file_id or not peer_id:
            return jsonify({
                'success': False,
                'error': 'Paramètres manquants'
            }), 400
        
        # Vérifier si le fichier appartient à ce peer
        my_peer_id = _peer_app.peer_id
        if peer_id == my_peer_id and not force_download:
            return jsonify({
                'success': False,
                'error': 'own_file',  # Code spécial pour identifier que c'est son propre fichier
                'message': 'Ce fichier vous appartient. Voulez-vous vraiment le télécharger ?'
            }), 400
        
        # Démarrer le téléchargement
        job = _peer_app.download_file(file_id, peer_id)
        
        if job:
            return jsonify({
                'success': True,
                'job_id': job.id,
                'message': 'Téléchargement démarré'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Impossible de démarrer le téléchargement'
            }), 500
        
    except Exception as e:
        logger.error(f"Erreur API start download : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/download/<job_id>/cancel', methods=['POST'])
def api_cancel_download(job_id):
    """
    API : Annule un téléchargement.
    """
    try:
        success = _peer_app.peer_client.cancel_download(job_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Téléchargement annulé'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Téléchargement introuvable ou déjà terminé'
            }), 404
        
    except Exception as e:
        logger.error(f"Erreur API cancel download : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/download/<job_id>/status')
def api_download_status(job_id):
    """
    API : Statut d'un téléchargement.
    """
    try:
        job = _peer_app.peer_client.get_download(job_id)
        
        if job:
            return jsonify({
                'success': True,
                'job': job.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Téléchargement introuvable'
            }), 404
        
    except Exception as e:
        logger.error(f"Erreur API download status : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/download/<file_id>')
def download_file(file_id: str):
    """
    Sert un fichier pour téléchargement par un autre peer.
    
    Args:
        file_id: ID du fichier à télécharger
        
    Returns:
        Fichier en streaming
    """
    try:
        if _peer_app is None:
            logger.error("Application non initialisée")
            return jsonify({'error': 'Application non initialisée'}), 500
        
        # Récupérer les informations du fichier
        file_info = _peer_app.file_scanner.get_file_by_id(file_id)
        
        if file_info is None:
            logger.error(f"Fichier non trouvé : {file_id}")
            return jsonify({'error': 'Fichier non trouvé'}), 404
        
        # Obtenir le chemin complet du fichier
        file_path = _peer_app.file_scanner.get_file_path(file_info)
        
        if not file_path.exists():
            logger.error(f"Fichier physique introuvable : {file_path}")
            return jsonify({'error': 'Fichier physique introuvable'}), 404
        
        logger.info(f"📤 Envoi du fichier : {file_info.name} ({file_id[:8]}...) vers peer distant")
        
        # Envoyer le fichier
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_info.name,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du fichier {file_id} : {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@peer_bp.route('/api/downloads')
def api_list_downloads():
    """
    API : Liste de tous les téléchargements.
    """
    try:
        downloads = _peer_app.peer_client.get_all_downloads()
        
        return jsonify({
            'success': True,
            'downloads': [d.to_dict() for d in downloads]
        })
        
    except Exception as e:
        logger.error(f"Erreur API list downloads : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/peers/discovered')
def api_discovered_peers():
    """
    API : Liste des peers découverts (UDP).
    """
    try:
        peers = _peer_app.udp_discovery.get_discovered_peers()
        
        return jsonify({
            'success': True,
            'peers': [p.to_dict() for p in peers]
        })
        
    except Exception as e:
        logger.error(f"Erreur API discovered peers : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/peers/cache')
def api_cached_peers():
    """
    API : Liste des peers en cache.
    """
    try:
        peers = _peer_app.cache_manager.get_all_peers()
        
        return jsonify({
            'success': True,
            'peers': [p.to_dict() for p in peers]
        })
        
    except Exception as e:
        logger.error(f"Erreur API cached peers : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/tracker/status')
def api_tracker_status():
    """
    API : Statut de la connexion au tracker.
    """
    try:
        status = _peer_app.get_tracker_status()
        
        return jsonify({
            'success': True,
            'status': status.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Erreur API tracker status : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/tracker/reconnect', methods=['POST'])
def api_tracker_reconnect():
    """
    API : Force la reconnexion au tracker.
    """
    try:
        success = _peer_app.connect_to_tracker()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Reconnecté au tracker'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Échec de la reconnexion'
            }), 500
        
    except Exception as e:
        logger.error(f"Erreur API tracker reconnect : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/statistics')
def api_statistics():
    """
    API : Statistiques générales du peer.
    """
    try:
        stats = _peer_app.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Erreur API statistics : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/cache/clear', methods=['POST'])
def api_clear_cache():
    """
    API : Efface le cache local.
    """
    try:
        _peer_app.cache_manager.clear_all()
        
        return jsonify({
            'success': True,
            'message': 'Cache effacé'
        })
        
    except Exception as e:
        logger.error(f"Erreur API clear cache : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """
    API : Gestion des paramètres.
    """
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'settings': _peer_app.config
            })
        else:
            # TODO: Implémenter la mise à jour des paramètres
            return jsonify({
                'success': False,
                'error': 'Modification des paramètres non implémentée'
            }), 501
        
    except Exception as e:
        logger.error(f"Erreur API settings : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/peers/all')
def api_all_peers():
    """
    API : Liste de tous les peers connus (tracker + UDP).
    """
    try:
        import requests
        
        peers_list = []
        
        # 1. Récupérer les peers depuis le tracker
        if _peer_app.tracker_connected and _peer_app.tracker_url:
            try:
                response = requests.get(
                    f"{_peer_app.tracker_url}/api/peers",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    tracker_peers = data.get('peers', [])
                    
                    # Filtrer pour exclure le peer actuel
                    for peer in tracker_peers:
                        if peer.get('id') != _peer_app.peer_id:
                            peers_list.append({
                                'id': peer.get('id'),
                                'name': peer.get('name'),
                                'ip_address': peer.get('ip_address'),
                                'port': peer.get('port'),
                                'status': peer.get('status'),
                                'is_online': peer.get('is_online', False),
                                'source': 'tracker'
                            })
            except Exception as e:
                logger.warning(f"Erreur récupération peers depuis tracker : {e}")
        
        # 2. Ajouter les peers découverts via UDP
        udp_peers = _peer_app.udp_discovery.get_discovered_peers()
        for peer in udp_peers:
            # Vérifier si déjà dans la liste
            if not any(p['id'] == peer.id for p in peers_list):
                peers_list.append({
                    'id': peer.id,
                    'name': peer.name,
                    'ip_address': peer.ip_address,
                    'port': peer.port,
                    'status': peer.status,
                    'is_online': True,
                    'source': 'udp'
                })
        
        return jsonify({
            'success': True,
            'count': len(peers_list),
            'peers': peers_list
        })
        
    except Exception as e:
        logger.error(f"Erreur API all peers : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/files/<file_id>/permissions', methods=['POST'])
def api_update_file_permissions(file_id):
    """
    API : Met à jour les permissions d'un fichier local.
    
    Body JSON:
        - is_private: true/false
        - allowed_peers: liste des peer_id autorisés
    """
    try:
        import requests
        
        data = request.get_json()
        is_private = data.get('is_private', False)
        allowed_peers = data.get('allowed_peers', [])
        
        # Vérifier que le fichier existe localement
        file_info = _peer_app.file_scanner.get_file_by_id(file_id)
        
        if not file_info:
            return jsonify({
                'success': False,
                'error': 'Fichier non trouvé'
            }), 404
        
        # Mettre à jour les permissions localement
        file_info.is_private = is_private
        file_info.allowed_peers = allowed_peers if is_private else None
        
        # Mettre à jour dans l'index
        _peer_app.file_scanner.files_index[file_id] = file_info
        
        # Synchroniser avec le tracker
        if _peer_app.tracker_connected and _peer_app.tracker_url:
            try:
                response = requests.post(
                    f"{_peer_app.tracker_url}/api/file/{file_id}/permissions",
                    json={
                        'peer_id': _peer_app.peer_id,
                        'is_private': is_private,
                        'allowed_peers': allowed_peers
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.warning(f"Erreur synchronisation permissions avec tracker : {response.status_code}")
            except Exception as e:
                logger.warning(f"Erreur mise à jour tracker : {e}")
        
        logger.info(f"✅ Permissions mises à jour pour {file_info.name} : is_private={is_private}")
        
        return jsonify({
            'success': True,
            'message': 'Permissions mises à jour',
            'file': file_info.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Erreur mise à jour permissions : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/files/<file_id>', methods=['DELETE'])
def api_delete_file(file_id):
    """
    API : Supprimer un fichier partagé.
    """
    try:
        import requests
        import os
        
        # Vérifier que le fichier existe
        if file_id not in _peer_app.file_scanner.files_index:
            return jsonify({
                'success': False,
                'error': 'Fichier non trouvé'
            }), 404
        
        file_info = _peer_app.file_scanner.files_index[file_id]
        file_path = Path(_peer_app.config['peer']['shared_folder']) / file_info.name
        
        # Supprimer le fichier physique
        if file_path.exists():
            os.remove(file_path)
            logger.info(f"Fichier physique supprimé : {file_path}")
        
        # Retirer de l'index local
        del _peer_app.file_scanner.files_index[file_id]
        
        # Notifier le tracker
        if _peer_app.tracker_connected and _peer_app.tracker_url:
            try:
                response = requests.delete(
                    f"{_peer_app.tracker_url}/api/files/{file_id}",
                    json={'peer_id': _peer_app.peer_id},
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.warning(f"Erreur suppression tracker : {response.status_code}")
            except Exception as e:
                logger.warning(f"Erreur notification tracker : {e}")
        
        logger.info(f"✅ Fichier supprimé : {file_info.name}")
        
        return jsonify({
            'success': True,
            'message': 'Fichier supprimé'
        })
        
    except Exception as e:
        logger.error(f"Erreur suppression fichier : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/files/sync', methods=['POST'])
def api_sync_files():
    """
    API : Synchronise les fichiers locaux avec le tracker.
    Appelé après la configuration des permissions des nouveaux fichiers.
    """
    try:
        if _peer_app.tracker_connected:
            _peer_app.sync_files_with_tracker()
            return jsonify({
                'success': True,
                'message': 'Fichiers synchronisés avec le tracker'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Tracker non connecté'
            }), 503
            
    except Exception as e:
        logger.error(f"Erreur synchronisation : {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== ENDPOINTS POUR FRAGMENTATION DISTRIBUÉE ====================

@peer_bp.route('/api/chunks/store', methods=['POST'])
def api_store_chunk():
    """
    API : Stocke un chunk reçu d'un autre peer.
    
    Body params:
        - file_id (str): ID du fichier
        - chunk_index (int): Index du chunk
        - chunk_hash (str): Hash SHA-256 attendu
        - chunk_data (file): Données binaires du chunk
    """
    try:
        # Vérifier les paramètres
        if 'chunk_data' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Données du chunk manquantes'
            }), 400
        
        file_id = request.form.get('file_id')
        chunk_index = request.form.get('chunk_index', type=int)
        chunk_hash = request.form.get('chunk_hash')
        
        if not all([file_id, chunk_index is not None, chunk_hash]):
            return jsonify({
                'success': False,
                'error': 'Paramètres incomplets (file_id, chunk_index, chunk_hash requis)'
            }), 400
        
        # Lire les données du chunk
        chunk_file = request.files['chunk_data']
        chunk_data = chunk_file.read()
        
        # Stocker le chunk via le DistributedChunkManager
        success = _peer_app.distributed_chunk_manager.receive_chunk(
            file_id=file_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            chunk_hash=chunk_hash
        )
        
        if success:
            logger.info(f"Chunk {chunk_index} du fichier {file_id} stocké avec succès")
            return jsonify({
                'success': True,
                'message': f'Chunk {chunk_index} stocké',
                'chunk_index': chunk_index,
                'size': len(chunk_data)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Échec du stockage du chunk (hash invalide ou erreur I/O)'
            }), 500
            
    except Exception as e:
        logger.error(f"Erreur stockage chunk : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/chunks/<file_id>/<int:chunk_index>', methods=['GET'])
def api_get_chunk(file_id, chunk_index):
    """
    API : Récupère un chunk stocké localement pour le renvoyer à un autre peer.
    
    Path params:
        - file_id (str): ID du fichier
        - chunk_index (int): Index du chunk demandé
        
    Returns:
        Données binaires du chunk ou erreur 404
    """
    try:
        # Vérifier si on possède ce chunk (stocké par un autre peer)
        chunk_data = _peer_app.distributed_chunk_manager.get_stored_chunk(file_id, chunk_index)
        
        if chunk_data:
            # Vérifier l'intégrité avant l'envoi
            if _peer_app.distributed_chunk_manager.verify_stored_chunk(file_id, chunk_index):
                logger.info(f"Envoi du chunk {chunk_index} du fichier {file_id}")
                
                from io import BytesIO
                return send_file(
                    BytesIO(chunk_data),
                    mimetype='application/octet-stream',
                    as_attachment=True,
                    download_name=f'{file_id}_chunk_{chunk_index}.bin'
                )
            else:
                logger.error(f"Chunk {chunk_index} corrompu, refus d'envoi")
                return jsonify({
                    'success': False,
                    'error': 'Chunk corrompu'
                }), 500
        
        # Sinon, peut-être que ce chunk fait partie d'un fichier local
        file_info = _peer_app.cache_manager.get_file_info(file_id)
        if not file_info:
            return jsonify({
                'success': False,
                'error': f'Fichier {file_id} inconnu'
            }), 404
        
        # Vérifier si le fichier est distribué et si on possède ce chunk
        if file_info.is_chunked and file_info.distribution_map:
            import json
            distribution_map = json.loads(file_info.distribution_map)
            my_peer_id = _peer_app.config['peer']['id']
            
            # Ce chunk nous appartient-il dans la distribution ?
            if distribution_map.get(str(chunk_index)) == my_peer_id:
                # Lire depuis le fichier source
                shared_folder = Path(_peer_app.config['peer']['shared_folder'])
                filepath = shared_folder / file_info.name
                
                if filepath.exists():
                    chunk_data = _peer_app.chunk_manager.read_chunk(
                        filepath, 
                        chunk_index, 
                        file_info.size
                    )
                    
                    logger.info(f"Envoi du chunk {chunk_index} depuis fichier local {file_info.name}")
                    
                    from io import BytesIO
                    return send_file(
                        BytesIO(chunk_data),
                        mimetype='application/octet-stream',
                        as_attachment=True,
                        download_name=f'{file_id}_chunk_{chunk_index}.bin'
                    )
        
        # Chunk introuvable
        return jsonify({
            'success': False,
            'error': f'Chunk {chunk_index} introuvable'
        }), 404
        
    except Exception as e:
        logger.error(f"Erreur récupération chunk : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@peer_bp.route('/api/download/<job_id>/chunks_status', methods=['GET'])
def api_chunks_status(job_id):
    """
    API : Récupère le statut détaillé des chunks d'un téléchargement en cours.
    
    Path params:
        - job_id (str): ID du job de téléchargement
        
    Returns:
        {
            'success': True,
            'chunks_status': {
                0: {'status': 'completed', 'peer_id': 'peer-123'},
                1: {'status': 'downloading', 'peer_id': 'peer-456', 'progress': 45},
                2: {'status': 'pending', 'peer_id': 'peer-789'},
                3: {'status': 'failed', 'peer_id': 'peer-offline', 'error': 'Peer hors ligne'}
            },
            'total_chunks': 10,
            'completed_chunks': 5,
            'pending_chunks': 3,
            'failed_chunks': 2
        }
    """
    try:
        # Récupérer le job de téléchargement
        download_job = _peer_app.get_download_status(job_id)
        
        if not download_job:
            return jsonify({
                'success': False,
                'error': f'Job {job_id} introuvable'
            }), 404
        
        # Si pas de chunks_progress, téléchargement non fragmenté
        if not hasattr(download_job, 'chunks_progress') or not download_job.chunks_progress:
            return jsonify({
                'success': True,
                'is_chunked': False,
                'message': 'Téléchargement non fragmenté'
            })
        
        # Calculer les statistiques
        chunks_status = download_job.chunks_progress
        total_chunks = len(chunks_status)
        completed = sum(1 for c in chunks_status.values() if c.get('status') == 'completed')
        pending = sum(1 for c in chunks_status.values() if c.get('status') == 'pending')
        failed = sum(1 for c in chunks_status.values() if c.get('status') == 'failed')
        downloading = sum(1 for c in chunks_status.values() if c.get('status') == 'downloading')
        
        return jsonify({
            'success': True,
            'is_chunked': True,
            'chunks_status': chunks_status,
            'statistics': {
                'total_chunks': total_chunks,
                'completed_chunks': completed,
                'downloading_chunks': downloading,
                'pending_chunks': pending,
                'failed_chunks': failed,
                'progress_percent': (completed / total_chunks * 100) if total_chunks > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Erreur statut chunks : {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500