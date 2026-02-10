# 🚂 Déploiement Railway - Guide Pas à Pas

Ce guide vous accompagne étape par étape pour déployer votre application P2P sur Railway.app.

## ✅ Prérequis

- Un compte GitHub
- Git installé sur votre machine
- Le code du projet

## 📝 Étape 1 : Préparer le dépôt Git

### 1.1 Initialiser Git (si pas déjà fait)

```bash
cd /home/utilisateur/Documents/Distributed_file_sharing
git init
```

### 1.2 Ajouter tous les fichiers

```bash
git add .
```

### 1.3 Faire le premier commit

```bash
git commit -m "Initial commit - P2P File Sharing ready for Railway"
```

### 1.4 Créer un dépôt GitHub

**Option A : Via l'interface GitHub**
1. Allez sur https://github.com/new
2. Nom : `p2p-file-sharing`
3. Description : `Réseau P2P de partage de fichiers décentralisé`
4. Public ou Privé (votre choix)
5. Ne cochez RIEN (pas de README, .gitignore, etc.)
6. Cliquez "Create repository"

**Option B : Via GitHub CLI (si installé)**
```bash
gh repo create p2p-file-sharing --public --source=. --remote=origin --push
```

### 1.5 Pousser le code vers GitHub

```bash
git remote add origin https://github.com/VOTRE-USERNAME/p2p-file-sharing.git
git branch -M main
git push -u origin main
```

## 🚀 Étape 2 : Déployer sur Railway

### 2.1 Créer un compte Railway

1. Allez sur https://railway.app
2. Cliquez sur "Login" (en haut à droite)
3. Choisissez "Login with GitHub"
4. Autorisez Railway à accéder à votre compte GitHub

### 2.2 Créer un nouveau projet

1. Une fois connecté, cliquez sur "New Project"
2. Sélectionnez "Deploy from GitHub repo"
3. Choisissez le dépôt `p2p-file-sharing`
4. Railway commence automatiquement le déploiement !

### 2.3 Attendre le déploiement

Railway va :
- ✅ Détecter que c'est une app Python
- ✅ Installer les dépendances (`requirements.txt`)
- ✅ Lire le `Procfile` pour savoir comment démarrer
- ✅ Démarrer l'application

⏱️ Temps estimé : 2-3 minutes

### 2.4 Vérifier le déploiement

1. Dans Railway, allez dans "Deployments"
2. Vous devriez voir :
   ```
   ✓ Building
   ✓ Deploying
   ✓ Success
   ```

## 🌐 Étape 3 : Obtenir l'URL publique

### 3.1 Générer un domaine

1. Dans votre projet Railway, cliquez sur le service déployé
2. Allez dans l'onglet "Settings"
3. Scrollez jusqu'à "Domains"
4. Cliquez sur "Generate Domain"
5. Railway génère une URL : `https://votre-app-XXX.up.railway.app`

### 3.2 Tester l'application

Ouvrez l'URL dans votre navigateur :
- **Dashboard** : `https://votre-app.up.railway.app/`
- **API Status** : `https://votre-app.up.railway.app/api/peers`

## 🔧 Étape 4 : Configuration (Optionnel)

### 4.1 Ajouter des variables d'environnement

Si vous voulez configurer des variables :

1. Dans Railway, allez dans "Variables"
2. Ajoutez :
   ```
   FLASK_ENV=production
   PORT=5000
   SECRET_KEY=votre-clé-secrète-ici
   ```

### 4.2 Configurer le domaine personnalisé

Si vous avez un domaine :

1. Settings → Domains
2. Cliquez sur "Custom Domain"
3. Entrez : `p2p.votre-domaine.com`
4. Ajoutez l'enregistrement CNAME fourni dans votre DNS

## 📊 Étape 5 : Surveiller l'application

### 5.1 Voir les logs

1. Dans Railway, cliquez sur votre service
2. Allez dans "Logs"
3. Vous verrez en temps réel :
   ```
   [INFO] Tracker démarré sur le port 5000
   [INFO] Base de données initialisée
   ```

### 5.2 Métriques

1. Onglet "Metrics"
2. Voyez :
   - CPU usage
   - Memory usage
   - Network traffic

## 🔄 Étape 6 : Mises à jour automatiques

Railway redéploie automatiquement à chaque push sur GitHub !

```bash
# Faire des modifications
vim tracker/app.py

# Commit et push
git add .
git commit -m "Update: nouvelle fonctionnalité"
git push origin main
```

Railway détecte le push et redéploie automatiquement ! 🎉

## 💰 Coûts et limites

### Plan gratuit
- ✅ 500 heures/mois (≈ 20 jours)
- ✅ 100 GB de bande passante sortante
- ✅ 512 MB RAM
- ✅ Shared CPU

### Calcul du temps
```
500 heures / 30 jours = ~16.6 heures par jour
```

**Conseil** : Votre app peut tourner 16h/jour gratuitement, ou 24/7 pendant 20 jours.

### Pour un usage 24/7
- Plan "Hobby" : $5/mois (500 heures gratuites incluses)
- Au-delà : ~$0.20/GB RAM/mois

## 🐛 Dépannage

### Le build échoue

**Erreur** : `ModuleNotFoundError`
```bash
# Vérifiez requirements.txt
cat requirements.txt

# Assurez-vous que tous les packages sont listés
```

**Erreur** : `Port already in use`
```python
# Utilisez la variable PORT de Railway
port = int(os.environ.get('PORT', 5000))
```

### L'app se met en erreur après démarrage

**Vérifiez les logs** dans Railway :
```bash
# Logs → View all logs
# Cherchez les erreurs Python
```

**Base de données perdue** :
- Railway Free Tier a un stockage persistant
- Mais redémarrages peuvent causer des pertes
- Solution : Utilisez une base PostgreSQL externe

### Impossible d'accéder à l'URL

1. Vérifiez que le domaine est bien généré
2. Attendez 1-2 minutes après le déploiement
3. Essayez en navigation privée
4. Vérifiez les logs pour les erreurs

## 📱 Étape 7 : Mettre à jour les scripts de téléchargement

Maintenant que votre tracker est en ligne, mettez à jour les scripts :

### Dans `run_p2p_linux.sh`
```bash
# Ligne ~120, changez l'URL par défaut
TRACKER_URL=${TRACKER_URL:-https://votre-app.up.railway.app}
```

### Dans `run_p2p_windows.bat`
```batch
REM Ligne ~80, changez l'URL
if "%TRACKER_URL%"=="" set TRACKER_URL=https://votre-app.up.railway.app
```

### Dans `download_page.html`
```html
<!-- Mettez à jour le lien vers l'API -->
<p>Connectez-vous au tracker : <a href="https://votre-app.up.railway.app">
  https://votre-app.up.railway.app
</a></p>
```

Puis push les modifications :
```bash
git add .
git commit -m "Update tracker URL to Railway deployment"
git push origin main
```

## 🎉 Terminé !

Votre application P2P est maintenant en ligne et accessible partout dans le monde !

**Prochaines étapes :**
1. Partagez l'URL avec vos utilisateurs
2. Déployez la page de téléchargement sur Vercel/GitHub Pages
3. Configurez un domaine personnalisé
4. Ajoutez des peers qui se connectent à votre tracker

**URLs importantes :**
- 🏠 Tracker : `https://votre-app.up.railway.app`
- 📊 Dashboard : `https://votre-app.up.railway.app/dashboard`
- 📁 Files : `https://votre-app.up.railway.app/files`
- 🔌 API : `https://votre-app.up.railway.app/api/peers`

## 📞 Support Railway

- 📖 Documentation : https://docs.railway.app
- 💬 Discord : https://discord.gg/railway
- 🐦 Twitter : @Railway

---

**Bon déploiement ! 🚀🚂**
