# 🚀 Déploiement Rapide sur Railway

## ✅ Réponse Courte

**NON**, vous n'avez **PAS besoin de redéployer manuellement** à chaque fois !

Railway est configuré pour **déployer automatiquement** dès que vous poussez sur GitHub.

## 🎯 Pour Déployer Vos Changements

### Méthode Automatique (Recommandée)

```bash
./deploy_to_railway.sh
```

### Méthode Manuelle

```bash
# 1. Ajouter les fichiers
git add .

# 2. Committer
git commit -m "feat: Système peer web + corrections UI"

# 3. Pousser vers GitHub
git push origin main

# 4. Railway redéploie AUTOMATIQUEMENT (2-3 minutes)
```

C'est tout ! Railway surveille votre repository GitHub et redéploie automatiquement.

## 📊 Ce Qui Se Passe

```
Vous: git push origin main
  ↓
GitHub: Nouveau commit détecté
  ↓
Railway: 🔔 Nouveau déploiement détecté
  ↓
Railway: 🔨 Build du projet (1-2 min)
  ↓
Railway: 🚀 Déploiement (30s)
  ↓
Railway: ✅ Application mise à jour
```

## ⚙️ Migration de Base de Données

✅ **Automatique** : Le système applique automatiquement les migrations au démarrage

Les nouvelles colonnes (`is_web_peer`, `user_id`) seront ajoutées automatiquement sans perte de données.

## 🔍 Surveiller le Déploiement

1. Ouvrez https://railway.app/dashboard
2. Sélectionnez votre projet
3. Onglet "Deployments"
4. Regardez le statut :
   - 🔨 Building...
   - 🚀 Deploying...
   - ✅ Active

## 🎉 Après le Déploiement

Testez votre application Railway :
```bash
# Remplacez par votre URL Railway
open https://votre-app.railway.app
```

Fonctionnalités à tester :
- ✅ Connexion/Inscription
- ✅ Peer web créé automatiquement
- ✅ Upload de fichiers (max 100 MB)
- ✅ Download de fichiers web
- ✅ Liste des peers (web + desktop)

## 💡 Rappel

- **Chaque `git push`** = déploiement automatique
- **Testez localement** avant de pousser
- **Les données** sont conservées (migration automatique)
- **Rollback facile** depuis le dashboard Railway

---

**Documentation complète** : Voir `RAILWAY_AUTO_DEPLOY.md`
