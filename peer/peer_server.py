"""
Serveur peer pour recevoir les requêtes de téléchargement d'autres peers.
"""

import logging
import socket
from pathlib import Path
from threading import Thread
from typing import Optional, Callable
from flask import Flask, request, send_file, jsonify
from werkzeug.serving import make_server

from shared.models import FileInfo, ChunkInfo
from peer.file_scanner import FileScanner
from peer.chunk_manager import ChunkManager

logger = logging.getLogger(__name__)


class PeerServer:
    """
    Serveur HTTP pour servir les fichiers aux autres peers.
    """
    
    def __init__(self, host: str, port: int, file_scanner: FileScanner, 
                 chunk_manager: ChunkManager, config: dict):
        """
        Initialise le serveur peer.
        
        Args:
            host: Adresse d'écoute
            port: Port d'écoute
            file_scanner: Scanner de fichiers
            chunk_manager: Gestionnaire de chunks
            config: Configuration de l'application
        """
        self.host = host
        self.port = port
        self.file_scanner = file_scanner
        self.chunk_manager = chunk_manager
        self.config = config
        
        # Créer l'application Flask
        self.app = Flask(__name__)
        self._setup_routes()
        
        # Serveur
        self._server: Optional[make_server] = None
        self._server_thread: Optional[Thread] = None
        
        # Callbacks
        self.on_download_started: Optional[Callable] = None
        self.on_chunk_sent: Optional[Callable] = None
        
        logger.info(f"Serveur peer initialisé sur {host}:{port}")
    
    def _setup_routes(self):
        """
        Configure les routes de l'API peer.
        """
        
        @self.app.route('/ping', methods=['GET'])
        def ping():
            """Endpoint pour vérifier si le peer est en ligne."""
            return jsonify({
                'status': 'online',
                'peer_id': getattr(self, 'peer_id', 'unknown')
            })
        
        @self.app.route('/files', methods=['GET'])
        def list_files():
            """Liste tous les fichiers partagés."""
            files = self.file_scanner.get_files()
            return jsonify({
                'success': True,
                'files': [f.to_dict() for f in files]
            })
        
        @self.app.route('/file/<file_id>', methods=['GET'])
        def get_file_info(file_id):
            """Obtient les informations d'un fichier."""
            file_info = self.file_scanner.get_file_by_id(file_id)
            
            if not file_info:
                return jsonify({
                    'success': False,
                    'error': 'Fichier non trouvé'
                }), 404
            
            return jsonify({
                'success': True,
                'file': file_info.to_dict()
            })
        
        @self.app.route('/download/<file_id>', methods=['GET'])
        def download_file(file_id):
            """Télécharge un fichier complet."""
            logger.info(f"📥 Requête de téléchargement reçue pour fichier {file_id} depuis {request.remote_addr}")
            
            file_info = self.file_scanner.get_file_by_id(file_id)
            
            if not file_info:
                logger.error(f"❌ Fichier {file_id} non trouvé dans l'index")
                return jsonify({
                    'success': False,
                    'error': 'Fichier non trouvé'
                }), 404
            
            filepath = self.file_scanner.get_file_path(file_info)
            
            if not filepath.exists():
                logger.error(f"❌ Fichier physique non trouvé : {filepath}")
                return jsonify({
                    'success': False,
                    'error': 'Fichier physique non trouvé'
                }), 404
            
            # Notifier le début du téléchargement
            if self.on_download_started:
                try:
                    peer_ip = request.remote_addr
                    self.on_download_started(file_info, peer_ip)
                except Exception as e:
                    logger.error(f"Erreur callback on_download_started: {e}")
            
            logger.info(f"✅ Envoi du fichier {file_info.name} à {request.remote_addr}")
            
            return send_file(
                str(filepath),
                as_attachment=True,
                download_name=file_info.name
            )
        
        @self.app.route('/download/<file_id>/chunk/<int:chunk_index>', methods=['GET'])
        def download_chunk(file_id, chunk_index):
            """Télécharge un chunk spécifique d'un fichier."""
            file_info = self.file_scanner.get_file_by_id(file_id)
            
            if not file_info:
                return jsonify({
                    'success': False,
                    'error': 'Fichier non trouvé'
                }), 404
            
            if not file_info.is_chunked:
                return jsonify({
                    'success': False,
                    'error': 'Fichier non fragmenté'
                }), 400
            
            # Vérifier l'index du chunk
            if chunk_index < 0 or chunk_index >= file_info.chunks_count:
                return jsonify({
                    'success': False,
                    'error': 'Index de chunk invalide'
                }), 400
            
            filepath = self.file_scanner.get_file_path(file_info)
            
            if not filepath.exists():
                return jsonify({
                    'success': False,
                    'error': 'Fichier physique non trouvé'
                }), 404
            
            try:
                # Lire le chunk
                chunk_data = self.chunk_manager.read_chunk(
                    filepath, chunk_index, file_info.size
                )
                
                # Obtenir les infos du chunk
                chunk_info = self.chunk_manager.get_chunk_info(
                    file_info.size, chunk_index, file_info.chunk_size
                )
                
                # Récupérer le hash attendu
                chunks_hashes = file_info.get_chunks_hashes_list()
                chunk_hash = chunks_hashes[chunk_index] if chunks_hashes else ''
                
                # Notifier l'envoi du chunk
                if self.on_chunk_sent:
                    try:
                        peer_ip = request.remote_addr
                        self.on_chunk_sent(file_info, chunk_index, peer_ip)
                    except Exception as e:
                        logger.error(f"Erreur callback on_chunk_sent: {e}")
                
                logger.debug(f"Envoi du chunk {chunk_index}/{file_info.chunks_count} "
                           f"de {file_info.name} à {request.remote_addr}")
                
                # Retourner les données avec métadonnées
                return jsonify({
                    'success': True,
                    'chunk': {
                        'index': chunk_index,
                        'size': len(chunk_data),
                        'hash': chunk_hash,
                        'data': chunk_data.hex()  # Encoder en hexadécimal
                    }
                })
                
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du chunk {chunk_index}: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/verify/<file_id>', methods=['GET'])
        def verify_file(file_id):
            """Vérifie l'existence et l'intégrité d'un fichier."""
            file_info = self.file_scanner.get_file_by_id(file_id)
            
            if not file_info:
                return jsonify({
                    'success': False,
                    'error': 'Fichier non trouvé'
                }), 404
            
            filepath = self.file_scanner.get_file_path(file_info)
            
            if not filepath.exists():
                return jsonify({
                    'success': True,
                    'exists': False
                })
            
            # Vérifier le hash si demandé
            verify_hash = request.args.get('verify_hash', 'false').lower() == 'true'
            
            if verify_hash:
                from shared.crypto import verify_hash
                is_valid = verify_hash(
                    filepath,
                    file_info.hash,
                    self.config['security']['hash_algorithm']
                )
                
                return jsonify({
                    'success': True,
                    'exists': True,
                    'valid': is_valid
                })
            
            return jsonify({
                'success': True,
                'exists': True
            })
        
        @self.app.errorhandler(Exception)
        def handle_error(error):
            """Gestionnaire d'erreurs global."""
            logger.error(f"Erreur serveur peer: {error}")
            return jsonify({
                'success': False,
                'error': str(error)
            }), 500
    
    def start(self):
        """
        Démarre le serveur peer.
        """
        try:
            # Créer le serveur
            self._server = make_server(
                self.host,
                self.port,
                self.app,
                threaded=True
            )
            
            # Démarrer dans un thread
            self._server_thread = Thread(target=self._server.serve_forever)
            self._server_thread.daemon = True
            self._server_thread.start()
            
            logger.info(f"✅ Serveur peer démarré sur http://{self.host}:{self.port}")
            
        except OSError as e:
            logger.error(f"❌ Impossible de démarrer le serveur peer: {e}")
            raise
    
    def stop(self):
        """
        Arrête le serveur peer.
        """
        if self._server:
            logger.info("Arrêt du serveur peer...")
            self._server.shutdown()
            if self._server_thread:
                self._server_thread.join(timeout=5)
            logger.info("✅ Serveur peer arrêté")
    
    def is_running(self) -> bool:
        """
        Vérifie si le serveur est en cours d'exécution.
        
        Returns:
            True si en cours d'exécution, False sinon
        """
        return (self._server_thread is not None and 
                self._server_thread.is_alive())
    
    def get_url(self) -> str:
        """
        Obtient l'URL du serveur.
        
        Returns:
            URL complète du serveur
        """
        return f"http://{self.host}:{self.port}"