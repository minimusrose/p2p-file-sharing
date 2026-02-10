#!/bin/bash

# Script pour pousser sur GitHub et déployer sur Railway

echo "🚀 Déploiement P2P File Sharing"
echo ""

# Demander l'URL du repo GitHub
echo "📝 Créez d'abord votre repo sur GitHub : https://github.com/new"
echo ""
echo "Nom suggéré : p2p-file-sharing"
echo "Type : Public (ou Private, les deux fonctionnent)"
echo ""
read -p "Entrez l'URL de votre repo GitHub (ex: https://github.com/username/p2p-file-sharing.git) : " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ URL manquante"
    exit 1
fi

# Ajouter le remote
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"
echo "✅ Remote GitHub configuré"

# Push sur GitHub
echo ""
echo "📤 Push vers GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Code poussé sur GitHub avec succès !"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚂 Étapes suivantes - Déploiement Railway :"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Allez sur : https://railway.app"
    echo ""
    echo "2. Cliquez sur 'Start a New Project'"
    echo ""
    echo "3. Sélectionnez 'Deploy from GitHub repo'"
    echo ""
    echo "4. Autorisez Railway à accéder à GitHub"
    echo ""
    echo "5. Choisissez votre repo : p2p-file-sharing"
    echo ""
    echo "6. Railway va automatiquement :"
    echo "   - Détecter Python"
    echo "   - Installer les dépendances"
    echo "   - Lancer le Tracker"
    echo ""
    echo "7. Une fois déployé (2-3 min), cliquez sur :"
    echo "   Settings → Networking → Generate Domain"
    echo ""
    echo "8. Vous obtiendrez une URL type :"
    echo "   https://p2p-file-sharing-production.up.railway.app"
    echo ""
    echo "9. Testez votre Tracker :"
    echo "   https://votre-url.up.railway.app/dashboard"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📊 Liens utiles :"
    echo "   • Votre repo GitHub : $REPO_URL"
    echo "   • Railway Dashboard : https://railway.app/dashboard"
    echo "   • Guide complet : cat DEPLOYMENT_GUIDE.md"
    echo ""
    echo "💡 Astuce : Les déploiements futurs seront automatiques !"
    echo "   Chaque 'git push' redéploiera automatiquement sur Railway."
    echo ""
else
    echo ""
    echo "❌ Erreur lors du push"
    echo ""
    echo "Vérifiez :"
    echo "  1. L'URL du repo est correcte"
    echo "  2. Vous avez les droits d'accès"
    echo "  3. Vous êtes connecté à GitHub : git config credential.helper store"
    echo ""
fi
