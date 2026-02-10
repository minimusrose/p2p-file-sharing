"""
Client peer pour télécharger des fichiers depuis d'autres peers.
"""

import logging
import requests
from pathlib import Path
from typing import Optional, Callable, List
from threading import Thread, Event, Lock
from queue import Queue, Empty
import time

from shared.models import PeerInfo, FileInfo, DownloadJob, ChunkInfo
from shared.network import send_http_request, check_port_open
from shared.crypto import verify_hash, calculate_chunk_hash
from shared.constants import HTTP_TIMEOUT
from peer.chunk_manager import ChunkManager

logger = logging.getLogger(__name__)


class PeerClient:
    """
    Client pour télécharger des fichiers depuis d'autres peers.
    """
    
    def __init__(self, chunk_manager: ChunkManager, config: dict):
        """
        Initialise le client peer.
        
        Args:
            chunk_manager: Gestionnaire de chunks
            config: Configuration de l'application
        """
        self.chunk_manager = chunk_manager
        self.config = config
        
        # File d'attente des téléchargements
        self.download_queue: Queue[DownloadJob] = Queue()
        
        # Téléchargements actifs {job_id: DownloadJob}
        self.active_downloads: dict = {}
        self._downloads_lock = Lock()
        
        # Threads de téléchargement
        self._download_threads: List[Thread] = []
        self._stop_event = Event()
        
        # Callbacks
        self.on_download_progress: Optional[Callable] = None
        self.on_download_completed: Optional[Callable] = None
        self.on_download_failed: Optional[Callable] = None
        self.on_chunk_downloaded: Optional[Callable] = None
        
        # Configuration
        self.max_concurrent = config['limits']['max_concurrent_downloads']
        self.download_speed_limit = config['limits']['max_download_speed']
        
        logger.info("Client peer initialisé")
    
    def start(self):
        """
        Démarre les threads de téléchargement.
        """
        self._stop_event.clear()
        
        # Démarrer les threads worker
        for i in range(self.max_concurrent):
            thread = Thread(target=self._download_worker, args=(i,), daemon=True)
            thread.start()
            self._download_threads.append(thread)
        
        logger.info(f"Client peer démarré avec {self.max_concurrent} workers")
    
    def stop(self):
        """
        Arrête tous les téléchargements en cours.
        """
        logger.info("Arrêt du client peer...")
        
        self._stop_event.set()
        
        # Attendre la fin des threads
        for thread in self._download_threads:
            thread.join(timeout=5)
        
        self._download_threads.clear()
        
        logger.info("Client peer arrêté")
    
    def add_download(self, file_info: FileInfo, source_peer: PeerInfo, 
                    destination_path: str) -> DownloadJob:
        """
        Ajoute un téléchargement à la file d'attente.
        
        Args:
            file_info: Informations du fichier
            source_peer: Peer source
            destination_path: Chemin de destination
            
        Returns:
            DownloadJob créé
        """
        from shared.utils import generate_unique_id
        from datetime import datetime
        
        # Créer le job
        job = DownloadJob(
            id=generate_unique_id(),
            file_info=file_info,
            source_peer=source_peer,
            destination_path=destination_path,
            status='pending',
            started_at=datetime.now().isoformat()
        )
        
        # Initialiser le statut des chunks si fichier fragmenté
        if file_info.is_chunked:
            job.chunks_status = {
                i: 'pending' for i in range(file_info.chunks_count)
            }
        
        # Ajouter à la file
        with self._downloads_lock:
            self.active_downloads[job.id] = job
        
        self.download_queue.put(job)
        
        logger.info(f"Téléchargement ajouté : {file_info.name} depuis {source_peer.name}")
        
        return job
    
    def _download_worker(self, worker_id: int):
        """
        Worker thread pour traiter les téléchargements.
        
        Args:
            worker_id: ID du worker
        """
        logger.debug(f"Worker {worker_id} démarré")
        
        while not self._stop_event.is_set():
            try:
                # Récupérer un job (timeout pour vérifier stop_event)
                job = self.download_queue.get(timeout=1)
                
                logger.info(f"[Worker {worker_id}] Début téléchargement : {job.file_info.name}")
                
                # Télécharger le fichier
                if job.file_info.is_chunked:
                    self._download_chunked_file(job, worker_id)
                else:
                    self._download_whole_file(job, worker_id)
                
                self.download_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Erreur: {e}")
        
        logger.debug(f"Worker {worker_id} arrêté")
    
    def _download_whole_file(self, job: DownloadJob, worker_id: int):
        """
        Télécharge un fichier complet (non fragmenté).
        
        Args:
            job: Job de téléchargement
            worker_id: ID du worker
        """
        job.status = 'downloading'
        
        try:
            # URL du fichier
            url = f"http://{job.source_peer.ip_address}:{job.source_peer.port}/download/{job.file_info.id}"
            
            logger.info(f"[Worker {worker_id}] Connexion à {url}")
            logger.info(f"[Worker {worker_id}] Source peer: {job.source_peer.name} ({job.source_peer.ip_address}:{job.source_peer.port})")
            
            # Télécharger avec streaming
            response = requests.get(url, stream=True, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            logger.info(f"[Worker {worker_id}] Connexion établie, début du téléchargement")
            
            # Créer le dossier de destination
            dest_path = Path(job.destination_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Télécharger le fichier
            total_size = job.file_info.size
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._stop_event.is_set():
                        raise InterruptedError("Téléchargement annulé")
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Mettre à jour la progression
                        job.update_progress(downloaded, total_size)
                        
                        # Notifier
                        if self.on_download_progress:
                            self.on_download_progress(job)
                        
                        # Limiter la vitesse si configuré
                        if self.download_speed_limit > 0:
                            time.sleep(len(chunk) / (self.download_speed_limit * 1024))
            
            # Vérifier l'intégrité
            is_valid = verify_hash(
                dest_path,
                job.file_info.hash,
                self.config['security']['hash_algorithm']
            )
            
            if is_valid:
                job.status = 'completed'
                job.progress = 100.0
                from datetime import datetime
                job.completed_at = datetime.now().isoformat()
                
                logger.info(f"✅ Téléchargement terminé : {job.file_info.name}")
                
                if self.on_download_completed:
                    self.on_download_completed(job)
            else:
                raise ValueError("Hash du fichier invalide")
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            
            logger.error(f"❌ Échec téléchargement : {job.file_info.name} - {e}")
            
            if self.on_download_failed:
                self.on_download_failed(job)
    
    def _download_chunked_file(self, job: DownloadJob, worker_id: int):
        """
        Télécharge un fichier fragmenté chunk par chunk.
        
        Args:
            job: Job de téléchargement
            worker_id: ID du worker
        """
        job.status = 'downloading'
        
        try:
            dest_path = Path(job.destination_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Récupérer les hashes des chunks
            chunks_hashes = job.file_info.get_chunks_hashes_list()
            
            if not chunks_hashes:
                raise ValueError("Hashes de chunks manquants")
            
            # Déterminer quels chunks télécharger
            missing_chunks = self.chunk_manager.get_missing_chunks(
                dest_path,
                chunks_hashes,
                job.file_info.size
            )
            
            total_chunks = len(chunks_hashes)
            completed_chunks = total_chunks - len(missing_chunks)
            
            logger.info(f"Chunks à télécharger : {len(missing_chunks)}/{total_chunks}")
            
            # Télécharger les chunks manquants
            for chunk_index in missing_chunks:
                if self._stop_event.is_set():
                    raise InterruptedError("Téléchargement annulé")
                
                # Télécharger le chunk
                success = self._download_single_chunk(
                    job, chunk_index, chunks_hashes[chunk_index], dest_path
                )
                
                if success:
                    completed_chunks += 1
                    job.chunks_status[chunk_index] = 'completed'
                    
                    # Mettre à jour la progression
                    progress = (completed_chunks / total_chunks) * 100
                    job.progress = progress
                    
                    # Notifier
                    if self.on_chunk_downloaded:
                        self.on_chunk_downloaded(job, chunk_index)
                    
                    if self.on_download_progress:
                        self.on_download_progress(job)
                else:
                    job.chunks_status[chunk_index] = 'failed'
                    raise Exception(f"Échec téléchargement chunk {chunk_index}")
            
            # Vérification finale
            job.status = 'completed'
            job.progress = 100.0
            from datetime import datetime
            job.completed_at = datetime.now().isoformat()
            
            logger.info(f"✅ Téléchargement fragmenté terminé : {job.file_info.name}")
            
            if self.on_download_completed:
                self.on_download_completed(job)
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            
            logger.error(f"❌ Échec téléchargement fragmenté : {job.file_info.name} - {e}")
            
            if self.on_download_failed:
                self.on_download_failed(job)
    
    def _download_single_chunk(self, job: DownloadJob, chunk_index: int, 
                              expected_hash: str, dest_path: Path) -> bool:
        """
        Télécharge un chunk individuel.
        
        Args:
            job: Job de téléchargement
            chunk_index: Index du chunk
            expected_hash: Hash attendu
            dest_path: Chemin de destination
            
        Returns:
            True si succès, False sinon
        """
        try:
            # URL du chunk
            url = (f"http://{job.source_peer.ip_address}:{job.source_peer.port}"
                  f"/download/{job.file_info.id}/chunk/{chunk_index}")
            
            # Télécharger
            response = requests.get(url, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('success'):
                logger.error(f"Erreur serveur pour chunk {chunk_index}: {data.get('error')}")
                return False
            
            # Décoder les données
            chunk_data = bytes.fromhex(data['chunk']['data'])
            
            # Vérifier le hash
            actual_hash = calculate_chunk_hash(
                chunk_data,
                self.config['security']['hash_algorithm']
            )
            
            if actual_hash.lower() != expected_hash.lower():
                logger.error(f"Hash invalide pour chunk {chunk_index}")
                return False
            
            # Écrire le chunk
            self.chunk_manager.write_chunk(
                dest_path,
                chunk_index,
                chunk_data,
                job.file_info.size
            )
            
            logger.debug(f"Chunk {chunk_index} téléchargé et vérifié")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur téléchargement chunk {chunk_index}: {e}")
            return False
    
    def get_download(self, job_id: str) -> Optional[DownloadJob]:
        """
        Récupère un job de téléchargement.
        
        Args:
            job_id: ID du job
            
        Returns:
            DownloadJob ou None
        """
        with self._downloads_lock:
            return self.active_downloads.get(job_id)
    
    def get_all_downloads(self) -> List[DownloadJob]:
        """
        Récupère tous les téléchargements.
        
        Returns:
            Liste de DownloadJob
        """
        with self._downloads_lock:
            return list(self.active_downloads.values())
    
    def cancel_download(self, job_id: str) -> bool:
        """
        Annule un téléchargement.
        
        Args:
            job_id: ID du job
            
        Returns:
            True si annulé, False sinon
        """
        with self._downloads_lock:
            job = self.active_downloads.get(job_id)
            if job and job.status in ['pending', 'downloading']:
                job.status = 'cancelled'
                logger.info(f"Téléchargement annulé : {job.file_info.name}")
                return True
        return False
    
    def verify_peer_availability(self, peer: PeerInfo) -> bool:
        """
        Vérifie si un peer est disponible.
        
        Args:
            peer: Informations du peer
            
        Returns:
            True si disponible, False sinon
        """
        try:
            url = f"http://{peer.ip_address}:{peer.port}/ping"
            response = send_http_request(url, timeout=5)
            
            if response and response.status_code == 200:
                data = response.json()
                return data.get('status') == 'online'
            
        except Exception as e:
            logger.debug(f"Peer {peer.name} non disponible: {e}")
        
        return False
    
    def get_statistics(self) -> dict:
        """
        Retourne des statistiques sur les téléchargements.
        
        Returns:
            Dictionnaire de statistiques
        """
        with self._downloads_lock:
            downloads = list(self.active_downloads.values())
        
        completed = sum(1 for d in downloads if d.status == 'completed')
        failed = sum(1 for d in downloads if d.status == 'failed')
        active = sum(1 for d in downloads if d.status == 'downloading')
        pending = sum(1 for d in downloads if d.status == 'pending')
        
        total_bytes = sum(d.bytes_downloaded for d in downloads)
        
        return {
            'total_downloads': len(downloads),
            'completed': completed,
            'failed': failed,
            'active': active,
            'pending': pending,
            'total_bytes_downloaded': total_bytes,
            'queue_size': self.download_queue.qsize()
        }