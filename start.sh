#!/bin/bash

# Script de démarrage rapide pour le système P2P
# Crée automatiquement les dossiers nécessaires et lance les composants

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Système de Partage de Fichiers P2P${NC}"
echo -e "${BLUE}   Script de démarrage rapide${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}Erreur: config.yaml introuvable${NC}"
    echo -e "${RED}Assurez-vous d'être dans le répertoire du projet${NC}"
    exit 1
fi

# Créer les dossiers nécessaires
echo -e "${YELLOW}Création des dossiers...${NC}"
mkdir -p data/shared_files
mkdir -p data/downloads
mkdir -p logs
echo -e "${GREEN}✓ Dossiers créés${NC}"
echo ""

# Vérifier les dépendances Python
echo -e "${YELLOW}Vérification des dépendances Python...${NC}"
if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}Installation des dépendances...${NC}"
    pip3 install -r requirements.txt
    echo -e "${GREEN}✓ Dépendances installées${NC}"
else
    echo -e "${GREEN}✓ Dépendances déjà installées${NC}"
fi
echo ""

# Créer quelques fichiers de test si les dossiers sont vides
if [ ! "$(ls -A data/shared_files)" ]; then
    echo -e "${YELLOW}Création de fichiers de test...${NC}"
    echo "Ceci est un fichier de test" > data/shared_files/test_file.txt
    echo "Fichier de documentation" > data/shared_files/documentation.txt
    echo -e "${GREEN}✓ Fichiers de test créés${NC}"
fi
echo ""

# Menu de sélection
echo -e "${BLUE}Que souhaitez-vous lancer ?${NC}"
echo "1) Tracker uniquement"
echo "2) Tracker + Peer"
echo "3) Peer uniquement (sans tracker)"
echo "4) Tout arrêter"
echo ""
read -p "Votre choix (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}Lancement du Tracker...${NC}"
        python3 -m tracker.app
        ;;
    2)
        echo -e "${GREEN}Lancement du Tracker et du Peer...${NC}"
        echo -e "${YELLOW}Le Tracker sera lancé en arrière-plan${NC}"
        python3 -m tracker.app > logs/tracker.log 2>&1 &
        TRACKER_PID=$!
        sleep 3
        echo -e "${GREEN}✓ Tracker lancé (PID: $TRACKER_PID)${NC}"
        echo -e "${GREEN}  Dashboard: http://localhost:5000${NC}"
        echo ""
        echo -e "${GREEN}Lancement du Peer...${NC}"
        python3 -m peer.app > logs/peer1.log 2>&1 &
        PEER_PID=$!
        sleep 3
        echo -e "${GREEN}✓ Peer lancé (PID: $PEER_PID)${NC}"
        echo -e "${GREEN}  Interface: http://localhost:8001${NC}"
        
        echo ""
        echo -e "${BLUE}================================================${NC}"
        echo -e "${GREEN}✓ Système démarré !${NC}"
        echo -e "${BLUE}================================================${NC}"
        echo ""
        echo -e "${GREEN}Interfaces web disponibles:${NC}"
        echo "  - Tracker:  http://localhost:5000"
        echo "  - Peer:     http://localhost:8001"
        echo ""
        echo -e "${YELLOW}PIDs des processus:${NC}"
        echo "  - Tracker: $TRACKER_PID"
        echo "  - Peer:    $PEER_PID"
        echo ""
        echo -e "${YELLOW}Pour arrêter tous les processus:${NC}"
        echo "  kill $TRACKER_PID $PEER_PID"
        echo "  ou lancez: ./start.sh et choisissez option 4"
        echo ""
        echo -e "${YELLOW}Pour voir les logs:${NC}"
        echo "  tail -f logs/tracker.log"
        echo "  tail -f logs/peer1.log"
        echo ""
        echo "Appuyez sur Ctrl+C pour quitter"
        echo ""
        
        # Attendre indéfiniment
        wait
        ;;
    3)
        echo -e "${GREEN}Lancement du Peer (mode dégradé - sans tracker)...${NC}"
        echo -e "${YELLOW}Le peer utilisera la découverte UDP${NC}"
        python3 -m peer.app
        ;;
    4)
        echo -e "${YELLOW}Arrêt de tous les processus P2P...${NC}"
        pkill -f "python3 -m tracker.app" && echo -e "${GREEN}✓ Tracker arrêté${NC}" || echo -e "${YELLOW}Tracker non actif${NC}"
        pkill -f "python3 -m peer.app" && echo -e "${GREEN}✓ Peer arrêté${NC}" || echo -e "${YELLOW}Peer non actif${NC}"
        echo -e "${GREEN}Nettoyage terminé${NC}"
        ;;
    *)
        echo -e "${RED}Choix invalide${NC}"
        exit 1
        ;;
esac
