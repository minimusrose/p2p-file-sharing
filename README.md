# 🌐 Système de Partage de Fichiers P2P# Système de Partage de Fichiers P2P en Classe



Système distribué de partage de fichiers peer-to-peer avec tracker centralisé, permettant le partage sélectif et sécurisé de fichiers entre utilisateurs.## Description



## ✨ CaractéristiquesSystème de partage de fichiers peer-to-peer (P2P) conçu pour une classe, permettant aux étudiants de partager des fichiers entre eux. Le système utilise une architecture hybride avec un serveur tracker central et un mode dégradé basé sur la découverte UDP locale.



- **Partage P2P Direct** : Transfert direct de fichiers entre peers## Caractéristiques

- **Partage Sélectif** : Contrôle sur qui peut accéder à vos fichiers (public/privé)

- **Interface Moderne** : Interface web professionnelle avec Bootstrap 5- ✅ **Architecture hybride** : Serveur tracker + mode dégradé

- **Gestion Intuitive** : Configuration des permissions dès l'upload- ✅ **Fragmentation de fichiers** : Support des gros fichiers avec chunks

- **Découverte Automatique** : UDP local + tracker centralisé- ✅ **Découverte locale** : Fonctionne même si le tracker est hors ligne

- **Chunking** : Support des gros fichiers- ✅ **Interface web** : Dashboard et statistiques

- **Recherche** : Recherche rapide sur le réseau- ✅ **Cache local** : Résilience et performance

- ✅ **Reprise de téléchargement** : Reprendre les transferts interrompus

## 🚀 Démarrage Rapide

## Architecture

```bash

# Installation### Mode Normal

git clone <repository>```

cd Distributed_file_sharingPeer A ←→ Tracker (Serveur Central) ←→ Peer B

pip install -r requirements.txt```



# Démarrage### Mode Dégradé

./start.sh```

Peer A ←→ Découverte UDP ←→ Peer B

# Accès         (Broadcast LAN)

# Peer 1: http://localhost:8001```

# Peer 2: http://localhost:8101

```## Installation



## 📚 Utilisation### Prérequis

- Python 3.8 ou supérieur

### 1. Ajouter un Fichier- pip

- Aller sur **Mes Fichiers**

- Cliquer **"Ajouter des Fichiers"** ou glisser-déposer### Étapes

- **Modal s'ouvre automatiquement**

- Choisir **Public** ou **Privé** (avec sélection des utilisateurs)1. Cloner le projet

- Enregistrer```bash

git clone <url-du-repo>

### 2. Rechercher et Téléchargercd Distributed_file_sharing

- Aller sur **Réseau**```

- Rechercher un fichier

- Cliquer **"Télécharger"**2. Créer un environnement virtuel

```bash

### 3. Gérer vos Fichierspython -m venv venv

- **🔒 Modifier permissions**source venv/bin/activate  # Linux/Mac

- **🗑️ Supprimer**# ou

venv\Scripts\activate  # Windows

## 🏗️ Architecture```



```3. Installer les dépendances

Tracker (Port 5000)```bash

     ↓pip install -r requirements.txt

Peer 1 ↔ Peer 2 ↔ Peer N```

(8001)    (8101)    (...)

     ↓4. Créer les dossiers nécessaires

UDP Discovery (5555)```bash

```mkdir -p data/shared_files data/downloads logs

```

### Technologies

- Python 3.13, Flask 3.0.0## Configuration

- SQLite + SQLAlchemy

- Bootstrap 5, jQueryModifier le fichier `config.yaml` selon vos besoins :

- SHA-256 pour intégrité

- **Tracker** : Port, base de données

## 📁 Structure- **Peer** : Dossiers partagés, ports

- **Chunking** : Taille des chunks, seuil de fragmentation

```- **Discovery** : Paramètres UDP

peer/           # Application peer

  templates/    # Interface web## Utilisation

    dashboard.html

    my_files.html### Lancer le Tracker (Serveur Central)

    network.html

tracker/        # Tracker centralisé```bash

shared/         # Code partagépython -m tracker.app

data/           # Fichiers et téléchargements```

logs/           # Logs

```Le tracker sera accessible sur `http://localhost:5000`



## 🔒 Sécurité### Lancer un Peer (Client)



- Hash SHA-256 pour intégrité```bash

- Permissions au niveau fichierpython -m peer.app

- Filtrage automatique des recherches```

- Validation côté tracker et peer

Le peer trouvera automatiquement un port disponible entre 5001-5100.

## 📞 Support

### Interface Web

```bash

# Logs- **Tracker Dashboard** : `http://localhost:5000`

tail -f logs/*.log- **Peer Interface** : `http://localhost:<port_du_peer>`



# Redémarrage propre## Structure du Projet

./clean_restart.sh

``````

Distributed_file_sharing/

---├── tracker/          # Serveur central

├── peer/             # Application peer

**Version** : 2.0 | **Statut** : Production Ready ✅├── shared/           # Code partagé

├── static/           # Ressources web
├── data/             # Données et fichiers
├── tests/            # Tests unitaires
└── config.yaml       # Configuration
```

## Fonctionnalités

### Partage de Fichiers
1. Placer les fichiers dans `data/shared_files/`
2. Le scanner détecte automatiquement les nouveaux fichiers
3. Les fichiers sont annoncés au tracker (ou en broadcast)

### Téléchargement
1. Rechercher un fichier dans l'interface
2. Cliquer sur "Télécharger"
3. Les fichiers > 10 MB sont automatiquement fragmentés
4. La reprise est automatique en cas d'interruption

### Statistiques
- Nombre de peers connectés
- Fichiers les plus téléchargés
- Volume de données transféré
- Historique d'activité

## Mode Dégradé

Quand le tracker est indisponible :
- ✅ Utilisation du cache local
- ✅ Découverte des peers par broadcast UDP
- ✅ Téléchargements directs peer-to-peer
- ⚠️ Pas de statistiques globales

## Développement

### Lancer les tests
```bash
pytest tests/
```

### Structure de développement
Voir la documentation détaillée dans `/docs/`

## Technologies

- **Backend** : Flask, SQLAlchemy
- **Frontend** : HTML, CSS, JavaScript
- **Communication** : HTTP, UDP, WebSockets
- **Base de données** : SQLite

## Auteur

Projet réalisé dans le cadre de [contexte]

## Licence

[À définir]

## Support

Pour toute question ou problème, créer une issue sur le dépôt.