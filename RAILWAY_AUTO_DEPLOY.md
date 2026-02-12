# 🚂 Guide de Déploiement Railway

## 📋 Vue d'Ensemble

Railway est configuré pour **déployer automatiquement** dès que vous poussez du code sur GitHub.

## ✅ Déploiement Automatique (Méthode Recommandée)

### Prérequis
- ✅ Projet Railway connecté à GitHub (déjà fait)
- ✅ Repository GitHub : `minimusrose/p2p-file-sharing`
- ✅ Auto-deploy activé sur Railway

### Processus Simple

```bash
# 1. Voir les changements
git status

# 2. Ajouter tous les fichiers modifiés
git add .

# 3. Committer avec un message descriptif
git commit -m "Description des changements"

# 4. Pousser vers GitHub
git push origin main

# 5. Railway redéploie AUTOMATIQUEMENT (2-3 minutes)
```

### ⚡ Script Automatisé

Pour cette mise à jour spécifique :

```bash
./deploy_to_railway.sh
```

Ce script :
- ✅ Vérifie la branche
- ✅ Ajoute les fichiers modifiés
- ✅ Crée un commit détaillé
- ✅ Pousse vers GitHub
- ✅ Railway redéploie automatiquement

## 📦 Que Se Passe-t-il sur Railway ?

### 1. Détection du Push (Instant)
Railway surveille votre repository GitHub et détecte immédiatement le nouveau commit.

### 2. Build Automatique (1-2 min)
```
📦 Railway récupère le code
🔨 Installe les dépendances (requirements.txt)
🏗️  Build avec Nixpacks
```

### 3. Déploiement (30s - 1min)
```
🚀 Arrêt de l'ancienne version
🔄 Démarrage de la nouvelle version
🌐 Mise à jour de l'URL publique
✅ Service actif
```

### 4. Migration de Base de Données
⚠️ **ATTENTION** : Railway utilise des **volumes persistants**, donc :
- La base de données n'est **PAS** supprimée au redéploiement
- Les nouveaux champs doivent être ajoutés via **migration**

## 🗄️ Gestion de la Base de Données sur Railway

### Problème : Nouveaux Champs dans les Modèles

Vous avez ajouté :
- `Peer.is_web_peer` (Boolean)
- `Peer.user_id` (Integer, Foreign Key)

### Solutions

#### Option 1 : Reset Complet (Développement)
⚠️ **Perd toutes les données**

Sur Railway Dashboard :
1. Allez dans "Variables"
2. Créez une variable : `RESET_DB=true`
3. Redéployez
4. Supprimez la variable après le déploiement

Modifiez `tracker/app.py` pour gérer cette variable :
```python
import os
if os.environ.get('RESET_DB') == 'true':
    # Supprimer et recréer la base
    db_path = 'data/tracker.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.warning("⚠️  Base de données supprimée (RESET_DB=true)")
```

#### Option 2 : Migration avec Alembic (Production)
✅ **Conserve les données**

```bash
# Installer Alembic
pip install alembic

# Initialiser les migrations
alembic init migrations

# Créer une migration
alembic revision --autogenerate -m "Ajout champs peer web"

# Appliquer la migration
alembic upgrade head
```

#### Option 3 : Migration SQL Manuel (Simple)
✅ **Conserve les données**, rapide

Créez `tracker/migrations.py` :
```python
def migrate_database_to_v2(db_path):
    """Ajoute les colonnes pour le système peer web"""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Ajouter is_web_peer si inexistant
        cursor.execute("ALTER TABLE peers ADD COLUMN is_web_peer BOOLEAN DEFAULT 0")
        print("✅ Colonne is_web_peer ajoutée")
    except sqlite3.OperationalError:
        print("ℹ️  Colonne is_web_peer existe déjà")
    
    try:
        # Ajouter user_id si inexistant
        cursor.execute("ALTER TABLE peers ADD COLUMN user_id INTEGER")
        print("✅ Colonne user_id ajoutée")
    except sqlite3.OperationalError:
        print("ℹ️  Colonne user_id existe déjà")
    
    conn.commit()
    conn.close()
```

Puis dans `tracker/app.py` :
```python
from tracker.migrations import migrate_database_to_v2

# Après init_database(app)
db_path = 'data/tracker.db'
if os.path.exists(db_path):
    migrate_database_to_v2(db_path)
```

## 🔍 Surveillance du Déploiement

### Sur Railway Dashboard

1. Ouvrez https://railway.app/dashboard
2. Sélectionnez votre projet
3. Onglet **"Deployments"**
4. Vous verrez :
   ```
   🔨 Building...
   🚀 Deploying...
   ✅ Active
   ```

### Logs en Temps Réel

Sur Railway :
- Cliquez sur le déploiement en cours
- Onglet **"Logs"**
- Vous verrez les logs Python en direct

### Tester le Déploiement

```bash
# Obtenir l'URL de votre application
curl https://votre-app.railway.app/api/statistics

# Ou ouvrir dans le navigateur
open https://votre-app.railway.app
```

## ⚙️ Configuration Actuelle

### Fichiers Railway

**`railway.json`** :
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python -m tracker.app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**`Procfile`** :
```
web: python -m tracker.app
```

### Variables d'Environnement Railway

Créez ces variables sur Railway Dashboard :

```bash
# Port (automatique)
PORT=5000

# Mode Production
FLASK_ENV=production
PYTHONUNBUFFERED=1

# Pour reset DB (temporaire, à supprimer après)
# RESET_DB=true
```

## 🚨 Checklist de Déploiement

### Avant de Pousser

- [ ] Tester localement (`python -m tracker.app`)
- [ ] Vérifier les dépendances (`requirements.txt`)
- [ ] Vérifier `.gitignore` (pas de secrets/données sensibles)
- [ ] Commit avec message descriptif

### Après le Push

- [ ] Surveiller le build sur Railway Dashboard
- [ ] Vérifier les logs de déploiement
- [ ] Tester l'URL publique
- [ ] Vérifier que la base de données fonctionne
- [ ] Tester l'upload/download web

### En Cas de Problème

1. **Check Logs Railway** : Voir l'erreur exacte
2. **Rollback** : Railway Dashboard > Deployments > Ancien déploiement > "Redeploy"
3. **Variables** : Vérifier les variables d'environnement
4. **Database** : Si erreur de colonnes, appliquer migration

## 📊 Avantages du Déploiement Automatique

### ✅ Avantages

- **Rapide** : 2-3 minutes du push au déploiement
- **Automatique** : Pas de commandes manuelles
- **Versioning** : Chaque commit = 1 déploiement
- **Rollback** : Retour arrière facile
- **Logs** : Historique complet
- **Zero Downtime** : Bascule sans interruption

### ⚠️ Attention

- **Chaque push = déploiement** : Testez localement d'abord
- **Données persistantes** : La base de données n'est pas reset automatiquement
- **Secrets** : Ne jamais committer de clés/tokens
- **Breaking changes** : Nécessitent migration de base de données

## 🎯 Workflow Recommandé

### Développement Local

```bash
# Branche de développement
git checkout -b feature/nouvelle-fonctionnalite

# Développer et tester
python -m tracker.app

# Committer localement
git add .
git commit -m "WIP: nouvelle fonctionnalité"
```

### Déploiement

```bash
# Merger dans main
git checkout main
git merge feature/nouvelle-fonctionnalite

# Pousser vers GitHub (déclenche Railway)
git push origin main

# Railway déploie automatiquement
```

## 📝 Exemple de Déploiement Complet

```bash
# 1. Vérifier les changements
$ git status
modified:   tracker/models.py
modified:   tracker/routes.py
new file:   tracker/templates/my_files.html

# 2. Tester localement
$ python -m tracker.app
✅ Tracker démarré sur http://localhost:5000

# 3. Committer
$ git add .
$ git commit -m "feat: Système peer web avec upload 100MB"

# 4. Pousser
$ git push origin main
Enumerating objects: 15, done.
Writing objects: 100% (15/15), done.
To https://github.com/minimusrose/p2p-file-sharing
   abc1234..def5678  main -> main

# 5. Railway détecte et déploie
🔔 Railway: New deployment started
🔨 Building...
🚀 Deploying...
✅ Deployment successful!
🌐 https://p2p-file-sharing.railway.app

# 6. Tester
$ curl https://p2p-file-sharing.railway.app/api/statistics
{"success": true, "stats": {...}}
```

## 🆘 Dépannage Rapide

### Erreur : "Column not found"
```
Solution: Migration de base de données nécessaire
Voir: Option 3 - Migration SQL Manuel
```

### Build échoue
```
Solution: Vérifier requirements.txt et logs Railway
```

### App ne démarre pas
```
Solution: Vérifier les logs, variable PORT, commande de démarrage
```

### Changements non visibles
```
Solution: Vérifier que le déploiement est bien "Active" sur Railway
Cache navigateur: Ctrl+F5
```

## ✅ Résumé

**Pour déployer vos changements actuels** :

```bash
# Méthode Simple
./deploy_to_railway.sh

# OU Méthode Manuelle
git add .
git commit -m "feat: Peer web system + UI fixes"
git push origin main

# Railway déploie automatiquement en 2-3 minutes
```

**Railway = Git Push = Déploiement Automatique** 🚀
