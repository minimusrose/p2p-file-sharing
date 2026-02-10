#!/bin/bash

###############################################################################
# Script de lancement P2P File Sharing - Linux/macOS
# Téléchargez et exécutez ce script pour démarrer votre peer
###############################################################################

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         P2P File Sharing - Installation & Démarrage          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Détecter le système d'exploitation
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

print_info "Système détecté : ${MACHINE}"
echo ""

# Vérifier Python
print_info "Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python ${PYTHON_VERSION} installé"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    print_success "Python ${PYTHON_VERSION} installé"
    PYTHON_CMD="python"
else
    print_error "Python n'est pas installé !"
    echo ""
    echo "📥 Installation de Python :"
    if [ "$MACHINE" = "Linux" ]; then
        echo "   Ubuntu/Debian : sudo apt install python3 python3-pip"
        echo "   Fedora/RHEL   : sudo dnf install python3 python3-pip"
        echo "   Arch Linux    : sudo pacman -S python python-pip"
    elif [ "$MACHINE" = "Mac" ]; then
        echo "   macOS : brew install python3"
        echo "   Ou téléchargez depuis https://www.python.org/downloads/"
    fi
    exit 1
fi
echo ""

# Demander le mode d'installation
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Mode d'Installation                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "1) Installation complète (Tracker + Peer)"
echo "   → Pour héberger votre propre réseau P2P"
echo ""
echo "2) Peer uniquement"
echo "   → Pour rejoindre un réseau P2P existant"
echo ""
echo -n "Votre choix [1-2] : "
read -r INSTALL_MODE

case "$INSTALL_MODE" in
    1)
        MODE="full"
        print_info "Installation complète sélectionnée"
        ;;
    2)
        MODE="peer"
        print_info "Installation Peer uniquement"
        ;;
    *)
        print_error "Choix invalide"
        exit 1
        ;;
esac
echo ""

# Créer le répertoire d'installation
INSTALL_DIR="$HOME/.p2p_file_sharing"
print_info "Installation dans : ${INSTALL_DIR}"

if [ -d "$INSTALL_DIR" ]; then
    print_warning "Le répertoire existe déjà"
    echo -n "Voulez-vous réinstaller ? [o/N] : "
    read -r REINSTALL
    if [[ "$REINSTALL" =~ ^[Oo]$ ]]; then
        rm -rf "$INSTALL_DIR"
        print_success "Ancien répertoire supprimé"
    else
        print_info "Utilisation de l'installation existante"
    fi
fi

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Télécharger les fichiers (si pas en local)
if [ ! -f "requirements.txt" ]; then
    print_info "Téléchargement des fichiers..."
    
    # TODO: Remplacer par l'URL réelle de votre dépôt
    # git clone https://github.com/votre-repo/p2p-file-sharing.git .
    
    print_error "Veuillez télécharger manuellement les fichiers depuis GitHub"
    echo "   git clone https://github.com/VOTRE-REPO/p2p-file-sharing.git ${INSTALL_DIR}"
    exit 1
fi

# Créer un environnement virtuel
print_info "Création de l'environnement virtuel..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    print_success "Environnement virtuel créé"
else
    print_success "Environnement virtuel existe déjà"
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
print_info "Installation des dépendances..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_success "Dépendances installées"
echo ""

# Configuration
print_info "Configuration..."

if [ "$MODE" = "full" ]; then
    # Demander le port du tracker
    echo -n "Port du Tracker [5000] : "
    read -r TRACKER_PORT
    TRACKER_PORT=${TRACKER_PORT:-5000}
    
    # Demander le port du peer
    echo -n "Port du Peer [8001] : "
    read -r PEER_PORT
    PEER_PORT=${PEER_PORT:-8001}
    
    TRACKER_URL="http://localhost:${TRACKER_PORT}"
else
    # Mode peer uniquement
    echo -n "URL du Tracker [http://localhost:5000] : "
    read -r TRACKER_URL
    TRACKER_URL=${TRACKER_URL:-http://localhost:5000}
    
    echo -n "Port du Peer [8001] : "
    read -r PEER_PORT
    PEER_PORT=${PEER_PORT:-8001}
fi
echo ""

# Créer les répertoires nécessaires
mkdir -p data/shared_files data/downloads logs

# Démarrer les services
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                        Démarrage                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ "$MODE" = "full" ]; then
    print_info "Démarrage du Tracker..."
    nohup $PYTHON_CMD -m tracker.app > logs/tracker.log 2>&1 &
    TRACKER_PID=$!
    sleep 3
    
    if ps -p $TRACKER_PID > /dev/null; then
        print_success "Tracker démarré (PID: ${TRACKER_PID})"
        echo "$TRACKER_PID" > .tracker.pid
    else
        print_error "Échec du démarrage du Tracker"
        exit 1
    fi
fi

print_info "Démarrage du Peer..."
nohup $PYTHON_CMD -m peer.app > logs/peer.log 2>&1 &
PEER_PID=$!
sleep 3

if ps -p $PEER_PID > /dev/null; then
    print_success "Peer démarré (PID: ${PEER_PID})"
    echo "$PEER_PID" > .peer.pid
else
    print_error "Échec du démarrage du Peer"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    ✓ Installation Réussie !                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
print_success "Votre peer P2P est maintenant actif !"
echo ""
echo "📊 Interfaces Web :"
if [ "$MODE" = "full" ]; then
    echo "   • Tracker Dashboard : http://localhost:${TRACKER_PORT}"
fi
echo "   • Peer Interface    : http://localhost:${PEER_PORT}"
echo ""
echo "📁 Répertoires :"
echo "   • Fichiers partagés : ${INSTALL_DIR}/data/shared_files"
echo "   • Téléchargements   : ${INSTALL_DIR}/data/downloads"
echo "   • Logs              : ${INSTALL_DIR}/logs"
echo ""
echo "🛠️  Commandes utiles :"
echo "   • Voir les logs      : tail -f ${INSTALL_DIR}/logs/peer.log"
echo "   • Arrêter le peer    : ${INSTALL_DIR}/stop_p2p.sh"
echo "   • Redémarrer         : ${INSTALL_DIR}/restart_p2p.sh"
echo ""

# Créer le script d'arrêt
cat > stop_p2p.sh << 'STOP_SCRIPT'
#!/bin/bash
if [ -f .peer.pid ]; then
    kill $(cat .peer.pid) 2>/dev/null && echo "✓ Peer arrêté"
    rm .peer.pid
fi
if [ -f .tracker.pid ]; then
    kill $(cat .tracker.pid) 2>/dev/null && echo "✓ Tracker arrêté"
    rm .tracker.pid
fi
STOP_SCRIPT
chmod +x stop_p2p.sh

# Créer le script de redémarrage
cat > restart_p2p.sh << 'RESTART_SCRIPT'
#!/bin/bash
./stop_p2p.sh
sleep 2
./run_p2p_linux.sh
RESTART_SCRIPT
chmod +x restart_p2p.sh

print_success "Scripts de gestion créés"
echo ""
print_warning "Appuyez sur Entrée pour continuer..."
read -r

# Ouvrir le navigateur
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:${PEER_PORT}" &
elif command -v open &> /dev/null; then
    open "http://localhost:${PEER_PORT}" &
fi
