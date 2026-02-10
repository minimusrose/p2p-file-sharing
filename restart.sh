#!/bin/bash

###############################################################################
# Script de redémarrage rapide (sans nettoyage)
###############################################################################

echo "🔄 Redémarrage du système P2P..."
echo ""

# Arrêter les processus
echo "⏹️  Arrêt des processus..."
pkill -f "tracker.app" 2>/dev/null
pkill -f "peer.app" 2>/dev/null
sleep 2

# Démarrer le tracker
echo "📡 Démarrage du Tracker..."
python -m tracker.app > logs/tracker.log 2>&1 &
TRACKER_PID=$!
sleep 3

if ps -p $TRACKER_PID > /dev/null; then
    echo "✅ Tracker démarré (PID: $TRACKER_PID)"
else
    echo "❌ Erreur démarrage Tracker"
    exit 1
fi

# Démarrer Peer
echo "👤 Démarrage du Peer..."
python -m peer.app > logs/peer1.log 2>&1 &
PEER_PID=$!
sleep 3

if ps -p $PEER_PID > /dev/null; then
    echo "✅ Peer démarré (PID: $PEER_PID)"
else
    echo "❌ Erreur démarrage Peer"
    exit 1
fi

echo ""
echo "✅ Système redémarré !"
echo ""
echo "📊 Interfaces :"
echo "   • Tracker Dashboard: http://localhost:5000"
echo "   • Peer: http://localhost:8001"
echo ""
echo "📝 Logs :"
echo "   • tail -f logs/tracker.log"
echo "   • tail -f logs/peer1.log"
echo ""
