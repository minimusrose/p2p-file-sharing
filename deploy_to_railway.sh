#!/bin/bash

# Script de déploiement automatique sur Railway via GitHub

echo "🚀 Déploiement de la nouvelle version avec système Peer Web"
echo ""

# Vérifier qu'on est sur la branche main
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    echo "⚠️  Vous n'êtes pas sur la branche main (actuellement sur: $current_branch)"
    read -p "Voulez-vous continuer ? (o/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Oo]$ ]]; then
        exit 1
    fi
fi

echo "📦 Ajout des fichiers modifiés..."
git add .gitignore
git add tracker/models.py
git add tracker/routes.py
git add tracker/templates/base.html
git add tracker/templates/dashboard.html
git add tracker/templates/my_files.html
git add WEB_PEER_GUIDE.md
git add migrate_db.py
git add web_uploads/.gitkeep

echo "✅ Fichiers ajoutés"
echo ""

echo "📝 Création du commit..."
git commit -m "feat: Ajout du système Peer Web

- Création automatique de peer web à la connexion
- Upload de fichiers via navigateur (max 100 MB)
- Download direct depuis le serveur tracker
- Nouvelle page 'Mes Fichiers' pour gestion web
- Corrections UI responsive (navbar + dashboard)
- Suppression du reload automatique du dashboard
- Ajout migration base de données
- Documentation complète (WEB_PEER_GUIDE.md)

Compatibilité: Les peers desktop et web coexistent"

echo "✅ Commit créé"
echo ""

echo "🔍 Affichage des changements..."
git log -1 --stat

echo ""
read -p "📤 Voulez-vous pousser vers GitHub (et déclencher le déploiement Railway) ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    echo "📤 Push vers GitHub..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Push réussi !"
        echo ""
        echo "🎉 Railway va maintenant redéployer automatiquement"
        echo "⏱️  Temps estimé: 2-3 minutes"
        echo ""
        echo "📊 Surveillez le déploiement sur:"
        echo "   https://railway.app/dashboard"
        echo ""
        echo "🌐 Une fois déployé, testez sur votre URL Railway"
    else
        echo "❌ Erreur lors du push"
        exit 1
    fi
else
    echo "⏸️  Push annulé. Vous pouvez le faire manuellement avec:"
    echo "   git push origin main"
fi
