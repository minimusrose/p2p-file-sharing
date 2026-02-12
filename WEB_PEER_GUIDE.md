# 🌐 Système de Peer Web - Guide d'Utilisation

## 📋 Vue d'Ensemble

Le système de partage P2P a été amélioré pour permettre le partage de fichiers **directement depuis le navigateur web**, sans avoir besoin de télécharger l'application desktop.

## ✨ Nouvelles Fonctionnalités

### 🎯 Peer Web Automatique

Dès qu'un utilisateur **se connecte** ou **s'inscrit** sur le site web :
- ✅ Un **peer web virtuel** est automatiquement créé pour lui
- ✅ Il apparaît dans la liste des peers du réseau
- ✅ Il peut partager et télécharger des fichiers immédiatement
- ✅ À la déconnexion, son peer passe en mode "hors ligne"

### 📤 Upload de Fichiers Web

**Page : "Mes Fichiers"** (`/files`)

- **Limite de taille** : 100 MB par fichier
- **Stockage** : Les fichiers sont stockés sur le serveur tracker dans `web_uploads/`
- **Format** : Tous types de fichiers acceptés
- **Visibilité** : Les fichiers uploadés sont **visibles par tous** (desktop + web)
- **Interface** : Barre de progression en temps réel, gestion intuitive

### 📥 Téléchargement de Fichiers

Deux types de fichiers sur le réseau :

1. **Fichiers Web** (uploadés via navigateur)
   - Badge "Web" + icône 🌐
   - Téléchargeables directement depuis le navigateur
   - Bouton "Télécharger" actif

2. **Fichiers Desktop** (partagés via application)
   - Badge "Desktop" + icône 💻
   - Nécessitent l'application desktop pour être téléchargés
   - Bouton grisé avec mention "App Desktop"

### 🗑️ Gestion des Fichiers

- **Supprimer** : Chaque utilisateur peut supprimer ses propres fichiers
- **Statistiques** : Compteur de téléchargements par fichier
- **Liste complète** : Voir tous les fichiers du réseau (web + desktop)

## 🔧 Architecture Technique

### Modèle de Données

**Modèle `Peer` (amélioré)** :
```python
class Peer(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100))
    is_web_peer = db.Column(db.Boolean, default=False)  # NOUVEAU
    user_id = db.Column(db.Integer, ForeignKey('users.id'))  # NOUVEAU
    # ... autres champs
```

**Modèle `User` (amélioré)** :
```python
class User(db.Model):
    # Relation vers le peer web
    web_peer = db.relationship('Peer', backref='web_user')
    uploaded_files = db.relationship('File', backref='uploader')
```

### Routes API

#### Upload Web
```
POST /web_upload
Content-Type: multipart/form-data
Authentification: Session requise

Paramètres:
- file: Le fichier à uploader (max 100 MB)

Réponse:
{
  "success": true,
  "message": "Fichier partagé avec succès !",
  "file_id": "abc123",
  "file_name": "document.pdf",
  "file_size": 1048576
}
```

#### Download Web
```
GET /web_download/<file_id>

Télécharge directement le fichier depuis le serveur.
Incrémente automatiquement le compteur de téléchargements.
```

#### Suppression
```
POST /web_delete/<file_id>
Authentification: Session requise

Supprime le fichier (physique + base de données).
Vérifie que l'utilisateur est bien le propriétaire.
```

### Stockage

```
web_uploads/
├── <hash>_fichier1.pdf
├── <hash>_image.jpg
└── <hash>_document.txt
```

Les fichiers sont nommés avec leur **hash SHA256 + nom original** pour :
- Éviter les collisions
- Permettre la déduplication
- Faciliter la vérification d'intégrité

## 🚀 Utilisation

### Côté Utilisateur Web

1. **Se connecter** sur http://localhost:5000
2. Automatiquement, vous devenez un **peer web**
3. Aller sur **"Mes Fichiers"**
4. **Uploader** des fichiers (max 100 MB)
5. **Voir** tous les fichiers du réseau
6. **Télécharger** les fichiers web directement
7. **Supprimer** vos propres fichiers

### Côté Utilisateur Desktop

L'application desktop continue de fonctionner normalement :
- Partage de fichiers sans limite de taille
- Fragmentation pour gros fichiers
- Découverte UDP locale
- **Nouveauté** : Les fichiers des peers web sont maintenant visibles !

## 📊 Distinction Web vs Desktop

### Dans l'Interface Web

| Caractéristique | Peer Web | Peer Desktop |
|----------------|----------|--------------|
| Icône | 🌐 Web | 💻 Desktop |
| Badge | Bleu "Web" | Gris "Desktop" |
| Upload max | 100 MB | Illimité |
| Download web | ✅ Direct | ❌ App requise |
| Stockage | Serveur tracker | Machine du peer |

### Dans la Base de Données

```python
# Peer Web
peer.is_web_peer = True
peer.user_id = 123  # Lien vers User
peer.port = 0  # Pas de serveur local

# Peer Desktop
peer.is_web_peer = False
peer.user_id = None
peer.port = 8001  # Serveur P2P actif
```

## 🔐 Sécurité

### Upload
- ✅ Authentification obligatoire
- ✅ Vérification de la taille (100 MB max)
- ✅ Hash SHA256 pour intégrité
- ✅ Nom de fichier sécurisé (secure_filename)

### Download
- ✅ Vérification d'existence du fichier
- ✅ Vérification du type de peer (web only)
- ✅ Compteurs de téléchargements

### Suppression
- ✅ Authentification obligatoire
- ✅ Vérification de propriété
- ✅ Suppression physique + base de données

## 🎨 Interface Utilisateur

### Page "Mes Fichiers"

```
┌─────────────────────────────────────────────┐
│ Mes Fichiers Web                            │
│ [Badge: Peer Web Actif]                     │
├─────────────────────────────────────────────┤
│ ℹ️ Info : Uploadez vos fichiers (max 100 MB)│
├─────────────────────────────────────────────┤
│ 📤 UPLOADER UN FICHIER                      │
│ [Choisir fichier] [Partager]               │
│ [Barre de progression]                      │
├─────────────────────────────────────────────┤
│ 📁 MES FICHIERS PARTAGÉS                   │
│ ┌───────────────────────────────────────┐  │
│ │ Nom │ Taille │ Date │ DL │ Actions    │  │
│ │ doc.pdf │ 2 MB │ ... │ 5 │ [↓][🗑️]  │  │
│ └───────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│ 🌐 TOUS LES FICHIERS DU RÉSEAU             │
│ [Liste avec badges Web/Desktop]            │
└─────────────────────────────────────────────┘
```

### Dashboard

Le dashboard affiche maintenant :
- ✅ **Badge "Peer Web Actif"** pour l'utilisateur connecté
- ✅ Bouton direct vers "Partager des Fichiers"
- ✅ Statistiques temps réel incluant les peers web

## 🧪 Tests Recommandés

### Test 1 : Inscription + Upload
1. S'inscrire avec un nouveau compte
2. Vérifier que le peer web est créé automatiquement
3. Uploader un fichier de 50 MB
4. Vérifier qu'il apparaît dans "Mes Fichiers"

### Test 2 : Visibilité Cross-Platform
1. Uploader un fichier via web
2. Lancer l'application desktop
3. Vérifier que le fichier web apparaît dans la liste
4. (Le download depuis desktop nécessitera des modifications)

### Test 3 : Limite de Taille
1. Essayer d'uploader un fichier de 150 MB
2. Vérifier le message d'erreur "Fichier trop volumineux"

### Test 4 : Download Web
1. Uploader un fichier
2. Le télécharger depuis un autre compte
3. Vérifier que le compteur de téléchargements s'incrémente

### Test 5 : Suppression
1. Uploader plusieurs fichiers
2. En supprimer un
3. Vérifier qu'il disparaît de la liste et du disque

## 📝 Notes Importantes

### Migration de Base de Données

⚠️ **IMPORTANT** : Les anciennes bases de données ne sont pas compatibles.

Si vous aviez une ancienne base :
```bash
python migrate_db.py  # Sauvegarde et supprime l'ancienne base
python -m tracker.app  # Crée la nouvelle base avec les nouveaux champs
```

### Fichiers Existants

Les fichiers uploadés avant cette mise à jour :
- Restent accessibles
- N'ont PAS de `uploaded_by_user_id` (sera NULL)
- Peuvent être considérés comme "orphelins"

### Performance

Pour un usage en production :
- Utiliser un serveur WSGI (Gunicorn, uWSGI)
- Configurer un reverse proxy (Nginx)
- Limiter le nombre de connexions simultanées
- Mettre en place un système de nettoyage automatique des vieux fichiers

## 🎉 Conclusion

Le système est maintenant **complet** et offre deux modes d'utilisation :

1. **Mode Web** : Partage léger, immédiat, sans installation (100 MB max)
2. **Mode Desktop** : Partage avancé, gros fichiers, fragmentation, P2P direct

Les deux modes coexistent et se complètent parfaitement ! 🚀
