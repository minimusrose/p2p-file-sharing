"""
Utilitaires réseau pour le système P2P.
"""

import socket
import logging
from typing import Optional, Tuple
import requests
from shared.constants import HTTP_TIMEOUT

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """
    Obtient l'adresse IP locale de la machine.
    
    Returns:
        Adresse IP locale (ex: '192.168.1.10')
    """
    try:
        # Créer une socket UDP (pas besoin de connexion réelle)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Se "connecter" à une adresse externe (Google DNS)
        # Cela ne crée pas de connexion réelle, juste pour obtenir l'IP locale
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.warning(f"Impossible d'obtenir l'IP locale: {e}, utilisation de localhost")
        return "127.0.0.1"


def get_public_ip() -> Optional[str]:
    """
    Obtient l'adresse IP publique (nécessite internet).
    
    Returns:
        Adresse IP publique ou None si échec
    """
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        logger.warning(f"Impossible d'obtenir l'IP publique: {e}")
    return None


def find_free_port(start_port: int = 5001, end_port: int = 5100) -> Optional[int]:
    """
    Trouve un port disponible dans une plage donnée.
    
    Args:
        start_port: Port de début
        end_port: Port de fin
        
    Returns:
        Numéro de port disponible ou None si aucun trouvé
    """
    for port in range(start_port, end_port + 1):
        if is_port_available(port):
            return port
    return None


def is_port_available(port: int, host: str = '0.0.0.0') -> bool:
    """
    Vérifie si un port est disponible.
    
    Args:
        port: Numéro de port à vérifier
        host: Adresse d'écoute
        
    Returns:
        True si le port est disponible, False sinon
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        return False


def check_port_open(ip: str, port: int, timeout: int = 2) -> bool:
    """
    Vérifie si un port est ouvert sur une machine distante.
    
    Args:
        ip: Adresse IP
        port: Numéro de port
        timeout: Timeout en secondes
        
    Returns:
        True si le port est ouvert, False sinon
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            return result == 0
    except Exception as e:
        logger.debug(f"Erreur lors de la vérification du port {ip}:{port}: {e}")
        return False


def send_http_request(url: str, method: str = 'GET', json_data: dict = None, 
                     timeout: int = HTTP_TIMEOUT) -> Optional[requests.Response]:
    """
    Envoie une requête HTTP avec gestion des erreurs.
    
    Args:
        url: URL de la requête
        method: Méthode HTTP (GET, POST, etc.)
        json_data: Données JSON à envoyer (pour POST/PUT)
        timeout: Timeout en secondes
        
    Returns:
        Objet Response ou None si erreur
    """
    try:
        if method.upper() == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(url, json=json_data, timeout=timeout)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=json_data, timeout=timeout)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, timeout=timeout)
        else:
            logger.error(f"Méthode HTTP non supportée: {method}")
            return None
        
        response.raise_for_status()
        return response
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout lors de la requête vers {url}")
    except requests.exceptions.ConnectionError:
        logger.error(f"Erreur de connexion vers {url}")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Erreur HTTP {e.response.status_code} pour {url}")
    except Exception as e:
        logger.error(f"Erreur lors de la requête vers {url}: {e}")
    
    return None


def create_udp_socket(bind_address: Tuple[str, int] = None, 
                      broadcast: bool = True) -> socket.socket:
    """
    Crée une socket UDP configurée.
    
    Args:
        bind_address: Adresse et port de binding (host, port)
        broadcast: Activer le broadcast
        
    Returns:
        Socket UDP configurée
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Permettre la réutilisation de l'adresse
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Activer le broadcast si demandé
    if broadcast:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # Bind si adresse fournie
    if bind_address:
        sock.bind(bind_address)
    
    return sock


def send_broadcast(message: bytes, port: int, local_ip: str = None) -> bool:
    """
    Envoie un message en broadcast UDP.
    
    Args:
        message: Message à envoyer (bytes)
        port: Port de destination
        local_ip: IP locale (pour calculer l'adresse de broadcast)
        
    Returns:
        True si succès, False sinon
    """
    try:
        sock = create_udp_socket(broadcast=True)
        
        # Adresse de broadcast
        broadcast_address = get_broadcast_address(local_ip) if local_ip else '255.255.255.255'
        
        sock.sendto(message, (broadcast_address, port))
        sock.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du broadcast: {e}")
        return False


def get_broadcast_address(local_ip: str) -> str:
    """
    Calcule l'adresse de broadcast pour un réseau local.
    
    Args:
        local_ip: Adresse IP locale
        
    Returns:
        Adresse de broadcast (ex: '192.168.1.255')
    """
    try:
        # Pour un réseau /24 typique
        parts = local_ip.split('.')
        if len(parts) == 4:
            parts[3] = '255'
            return '.'.join(parts)
    except Exception as e:
        logger.warning(f"Erreur calcul broadcast: {e}")
    
    # Fallback
    return '255.255.255.255'


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Résout un nom d'hôte en adresse IP.
    
    Args:
        hostname: Nom d'hôte à résoudre
        
    Returns:
        Adresse IP ou None si échec
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror as e:
        logger.error(f"Impossible de résoudre {hostname}: {e}")
        return None


def get_hostname() -> str:
    """
    Obtient le nom d'hôte de la machine.
    
    Returns:
        Nom d'hôte
    """
    try:
        return socket.gethostname()
    except Exception as e:
        logger.warning(f"Impossible d'obtenir le hostname: {e}")
        return "unknown"


def format_address(ip: str, port: int) -> str:
    """
    Formate une adresse IP:port.
    
    Args:
        ip: Adresse IP
        port: Port
        
    Returns:
        Chaîne formatée "ip:port"
    """
    return f"{ip}:{port}"


def parse_address(address: str) -> Optional[Tuple[str, int]]:
    """
    Parse une adresse "ip:port".
    
    Args:
        address: Adresse formatée "ip:port"
        
    Returns:
        Tuple (ip, port) ou None si erreur
    """
    try:
        parts = address.split(':')
        if len(parts) == 2:
            ip = parts[0]
            port = int(parts[1])
            return (ip, port)
    except Exception as e:
        logger.error(f"Erreur parsing adresse {address}: {e}")
    return None