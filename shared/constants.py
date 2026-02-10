"""
Constantes globales utilisées dans tout le projet.
"""

# Versions
VERSION = '1.0.0'

# Statuts des peers
PEER_STATUS_ONLINE = 'online'
PEER_STATUS_OFFLINE = 'offline'
PEER_STATUS_BUSY = 'busy'

# Statuts des téléchargements
DOWNLOAD_STATUS_PENDING = 'pending'
DOWNLOAD_STATUS_DOWNLOADING = 'downloading'
DOWNLOAD_STATUS_PAUSED = 'paused'
DOWNLOAD_STATUS_COMPLETED = 'completed'
DOWNLOAD_STATUS_FAILED = 'failed'
DOWNLOAD_STATUS_CANCELLED = 'cancelled'

# Types de messages UDP pour la découverte
MSG_TYPE_ANNOUNCE = 'ANNOUNCE'
MSG_TYPE_QUERY = 'QUERY'
MSG_TYPE_RESPONSE = 'RESPONSE'
MSG_TYPE_GOODBYE = 'GOODBYE'

# Modes de fonctionnement
MODE_NORMAL = 'normal'        # Tracker disponible
MODE_DEGRADED = 'degraded'    # Mode cache + découverte UDP

# Tailles
KB = 1024
MB = 1024 * KB
GB = 1024 * MB

# Timeouts réseau (en secondes)
HTTP_TIMEOUT = 10
UDP_TIMEOUT = 5
CONNECTION_RETRY_DELAY = 5

# Hash algorithms supportés
HASH_MD5 = 'md5'
HASH_SHA1 = 'sha1'
HASH_SHA256 = 'sha256'

# Messages d'erreur
ERROR_TRACKER_UNAVAILABLE = "Le serveur tracker est indisponible"
ERROR_PEER_OFFLINE = "Le peer propriétaire du fichier est hors ligne"
ERROR_FILE_NOT_FOUND = "Fichier introuvable"
ERROR_DOWNLOAD_FAILED = "Échec du téléchargement"
ERROR_INVALID_CHUNK = "Chunk invalide ou corrompu"
ERROR_DISK_SPACE = "Espace disque insuffisant"

# Messages de succès
SUCCESS_REGISTERED = "Enregistré avec succès sur le tracker"
SUCCESS_DOWNLOAD_COMPLETE = "Téléchargement terminé avec succès"
SUCCESS_FILE_SHARED = "Fichier partagé avec succès"

# Endpoints API du tracker
API_REGISTER = '/api/register'
API_UNREGISTER = '/api/unregister'
API_HEARTBEAT = '/api/heartbeat'
API_ANNOUNCE_FILES = '/api/announce_files'
API_SEARCH = '/api/search'
API_PEERS = '/api/peers'
API_FILE_PEERS = '/api/file/{file_id}/peers'
API_STATISTICS = '/api/statistics'
API_LOG_DOWNLOAD = '/api/log_download'

# Endpoints API du peer
API_PEER_FILES = '/files'
API_PEER_DOWNLOAD = '/download/{file_id}'
API_PEER_CHUNK = '/download/{file_id}/chunk/{chunk_index}'
API_PEER_PING = '/ping'

# Extensions de fichiers par catégorie
FILE_CATEGORIES = {
    'documents': ['.pdf', '.doc', '.docx', '.txt', '.odt', '.rtf'],
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
    'videos': ['.mp4', '.avi', '.mkv', '.mov', '.flv'],
    'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    'code': ['.py', '.java', '.cpp', '.js', '.html', '.css'],
}