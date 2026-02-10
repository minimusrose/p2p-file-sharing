# 🌐 Guide de Déploiement - P2P File Sharing

Ce guide vous explique comment héberger votre application P2P gratuitement en ligne.

## 📋 Table des matières

1. [Déployer sur Railway.app (Tracker)](#railway)
2. [Déployer sur Render.com (Tracker)](#render)
3. [Déployer sur Vercel (Page de téléchargement)](#vercel)
4. [Déployer sur GitHub Pages (Page de téléchargement)](#github-pages)
5. [Configuration DNS personnalisé](#dns)

---

## 🚂 Option 1 : Railway.app (Recommandé)

**Avantages :**
- ✅ 500h gratuites/mois ($5 de crédit)
- ✅ Déploiement Git automatique
- ✅ Base de données SQLite persistante
- ✅ Domaine HTTPS automatique
- ✅ Logs en temps réel

### Étapes :

1. **Créer un compte**
   - Allez sur https://railway.app
   - Connectez-vous avec GitHub

2. **Créer un nouveau projet**
   ```bash
   # Initialiser Git si pas déjà fait
   git init
   git add .
   git commit -m "Initial commit"
   
   # Créer un repo GitHub
   git remote add origin https://github.com/votre-username/p2p-file-sharing.git
   git push -u origin main
   ```

3. **Sur Railway.app**
   - Cliquez sur "New Project"
   - Sélectionnez "Deploy from GitHub repo"
   - Choisissez votre dépôt
   - Railway détecte automatiquement Python

4. **Variables d'environnement** (optionnel)
   - Allez dans "Variables"
   - Ajoutez :
     ```
     FLASK_ENV=production
     PORT=5000
     ```

5. **Déployer**
   - Cliquez sur "Deploy"
   - Attendez 2-3 minutes
   - Votre app est en ligne ! 🎉

6. **Obtenir l'URL**
   - Cliquez sur "Settings" → "Domains"
   - Générez un domaine : `votre-app.up.railway.app`

**Coût :** Gratuit (500h/mois = ~20 jours d'utilisation continue)

---

## 🎨 Option 2 : Render.com

**Avantages :**
- ✅ Totalement gratuit (avec limitations)
- ✅ Déploiement Git automatique
- ✅ SSL gratuit
- ✅ Sleep après 15min d'inactivité (se réveille automatiquement)

### Étapes :

1. **Créer un compte**
   - https://render.com
   - Connectez-vous avec GitHub

2. **Créer un Web Service**
   - Dashboard → "New +" → "Web Service"
   - Connectez votre repo GitHub
   - Render détecte `render.yaml`

3. **Configuration automatique**
   - Le fichier `render.yaml` est déjà configuré
   - Cliquez sur "Create Web Service"

4. **Déploiement**
   - Render build et déploie automatiquement
   - URL : `https://p2p-tracker.onrender.com`

**Note :** Service gratuit = sleep après 15min d'inactivité. Premier accès = 30s de réveil.

**Coût :** Gratuit (limité à 750h/mois)

---

## ⚡ Option 3 : Vercel (Page de téléchargement uniquement)

**Avantages :**
- ✅ CDN ultra-rapide
- ✅ Déploiement instantané
- ✅ SSL automatique
- ✅ Domaine personnalisé gratuit

### Étapes :

1. **Installer Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Déployer**
   ```bash
   vercel login
   vercel --prod
   ```

3. **URL obtenue**
   - `https://p2p-file-sharing.vercel.app`

**Alternative sans CLI :**
1. Allez sur https://vercel.com
2. "Import Project" → Sélectionnez votre repo
3. Déploiement automatique

**Coût :** Gratuit illimité

---

## 🐙 Option 4 : GitHub Pages (Page statique)

**Avantages :**
- ✅ Totalement gratuit
- ✅ Déploiement automatique via Actions
- ✅ Parfait pour la page de téléchargement

### Étapes :

1. **Push votre code sur GitHub**
   ```bash
   git add .
   git commit -m "Add deployment files"
   git push origin main
   ```

2. **Activer GitHub Pages**
   - Repo → Settings → Pages
   - Source : "GitHub Actions"
   - Le workflow `.github/workflows/pages.yml` est déjà configuré

3. **Attendez le déploiement**
   - Allez dans "Actions"
   - Le workflow se lance automatiquement
   - Après 2-3 minutes, votre site est en ligne

4. **URL**
   - `https://votre-username.github.io/p2p-file-sharing/`
   - Page de téléchargement : `https://votre-username.github.io/p2p-file-sharing/download_page.html`

**Coût :** Gratuit

---

## 🎯 Architecture Recommandée (Gratuite)

Combinez plusieurs services :

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  GitHub Pages / Vercel                                      │
│  └── Page de téléchargement (download_page.html)          │
│      └── Scripts: run_p2p_linux.sh, run_p2p_windows.bat   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Railway.app / Render.com                                   │
│  └── Tracker Backend (Python Flask)                        │
│      ├── API : /api/peers, /api/files, etc.               │
│      ├── Dashboard Web : /dashboard                        │
│      └── Interface d'upload : /files                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    Connexion des peers
```

### Configuration :

1. **Déployez la page de téléchargement sur Vercel/GitHub Pages**
   ```bash
   # Vercel
   vercel --prod
   
   # OU GitHub Pages (automatique après push)
   git push origin main
   ```

2. **Déployez le Tracker sur Railway**
   - Connectez votre repo
   - Railway détecte automatiquement Python
   - Obtenir l'URL : `https://votre-app.up.railway.app`

3. **Mettez à jour la page de téléchargement**
   - Éditez `download_page.html`
   - Remplacez les URLs des scripts par vos URLs réelles

4. **Mettez à jour les scripts**
   - Dans `run_p2p_linux.sh` et `run_p2p_windows.bat`
   - Changez l'URL du tracker par défaut :
     ```bash
     TRACKER_URL="https://votre-app.up.railway.app"
     ```

---

## 🔧 Configuration DNS personnalisé (Optionnel)

### Domaine personnalisé gratuit

1. **Obtenir un domaine gratuit**
   - https://www.freenom.com (domaines .tk, .ml, .ga, etc.)
   - Ou utiliser Cloudflare Pages (sous-domaine gratuit)

2. **Configurer sur Railway**
   - Settings → Domains → Add Custom Domain
   - Entrez : `p2p.votre-domaine.tk`
   - Ajoutez l'enregistrement CNAME fourni

3. **Configurer sur Vercel**
   - Project Settings → Domains
   - Add : `download.votre-domaine.tk`
   - Suivez les instructions DNS

---

## 📊 Comparaison des services

| Service | Tracker Backend | Page statique | Gratuit | Sleep | Base de données |
|---------|----------------|---------------|---------|-------|-----------------|
| **Railway** | ✅ Excellent | ❌ Non | 500h/mois | ❌ Non | ✅ Persistante |
| **Render** | ✅ Bon | ❌ Non | 750h/mois | ⚠️ Oui (15min) | ⚠️ Éphémère |
| **Vercel** | ❌ Non | ✅ Excellent | ✅ Illimité | ❌ Non | ❌ Non |
| **GitHub Pages** | ❌ Non | ✅ Bon | ✅ Illimité | ❌ Non | ❌ Non |
| **Heroku** | ✅ Bon | ❌ Non | ❌ Payant | ⚠️ Oui | ⚠️ Éphémère |

---

## 🚀 Déploiement Rapide (Commandes)

### Railway (Backend)
```bash
# Installation CLI
npm i -g @railway/cli

# Login
railway login

# Déploiement
railway init
railway up
railway open
```

### Vercel (Frontend)
```bash
# Installation CLI
npm i -g vercel

# Déploiement
vercel login
vercel --prod
```

### Render (Backend)
```bash
# Pas de CLI, utiliser l'interface web
# ou connecter directement le repo GitHub
```

### GitHub Pages (Frontend)
```bash
# Automatique après activation dans Settings
git push origin main
```

---

## 🛠️ Commandes Git utiles

```bash
# Initialiser Git
git init
git add .
git commit -m "Initial commit"

# Créer repo GitHub
gh repo create p2p-file-sharing --public --source=. --remote=origin --push

# Pousser les changements
git add .
git commit -m "Update deployment config"
git push origin main

# Créer une branche de production
git checkout -b production
git push -u origin production
```

---

## 🐛 Dépannage

### Le Tracker ne démarre pas sur Railway
- Vérifiez les logs : Railway Dashboard → View Logs
- Variables d'environnement manquantes ?
- Problème avec `requirements.txt` ?

### GitHub Pages ne se met pas à jour
- Allez dans "Actions" et vérifiez les erreurs
- Assurez-vous que GitHub Pages est activé
- Vérifiez la branche source (main ou gh-pages)

### Vercel : Build failed
- Vérifiez `vercel.json`
- Regardez les logs de build
- Essayez `vercel --debug`

### Base de données perdue sur Render
- Render Free Tier = stockage éphémère
- Solution : Utilisez Railway (stockage persistant)
- Ou connectez une base PostgreSQL externe

---

## 📞 Support

- **Railway** : https://railway.app/discord
- **Render** : https://render.com/docs
- **Vercel** : https://vercel.com/support
- **GitHub Pages** : https://docs.github.com/pages

---

## 🎉 Votre site est en ligne !

Après déploiement, partagez votre URL :
- **Page de téléchargement** : `https://votre-site.vercel.app`
- **Tracker API** : `https://votre-app.up.railway.app`
- **Dashboard** : `https://votre-app.up.railway.app/dashboard`

**Bon partage ! 🚀**
