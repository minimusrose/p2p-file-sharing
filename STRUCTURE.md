# Structure du Projet P2P File Sharing

```
Distributed_file_sharing/
│
├── README.md                    # Documentation principale du projet
├── requirements.txt             # Dépendances Python
├── config.yaml                  # Configuration du système
│
├── start.sh                     # Script de démarrage avec menu
├── restart.sh                   # Script de redémarrage rapide
│
├── tracker/                     # Serveur central (Tracker)
│   ├── __init__.py
│   ├── app.py                   # Application Flask du tracker
│   ├── routes.py                # Routes API du tracker
│   ├── models.py                # Modèles de données
│   ├── database.py              # Gestion de la base de données
│   └── templates/               # Templates HTML du dashboard
│       ├── base.html
│       ├── dashboard.html
│       └── statistics.html
│
├── peer/                        # Application Client (Peer)
│   ├── __init__.py
│   ├── app.py                   # Application Flask du peer
│   ├── routes.py                # Routes API et pages web
│   ├── file_scanner.py          # Scanner de fichiers
│   ├── cache_manager.py         # Gestion du cache local
│   ├── chunk_manager.py         # Gestion des chunks (fragmentation)
│   ├── discovery.py             # Découverte UDP des peers
│   ├── peer_server.py           # Serveur P2P pour transferts
│   ├── peer_client.py           # Client P2P pour téléchargements
│   ├── templates/               # Templates HTML
│   │   ├── base.html            # Template de base unifié
│   │   ├── dashboard.html       # Page d'accueil avec stats
│   │   ├── my_files.html        # Gestion des fichiers partagés
│   │   └── network.html         # Recherche et téléchargement
│   └── static/                  # Ressources statiques
│       ├── css/
│       │   └── peer.css         # Styles du peer
│       └── js/
│           └── peer.js          # JavaScript du peer
│
├── shared/                      # Code partagé entre tracker et peer
│   ├── __init__.py
│   ├── constants.py             # Constantes globales
│   ├── models.py                # Modèles de données partagés
│   ├── crypto.py                # Fonctions cryptographiques
│   ├── network.py               # Utilitaires réseau
│   └── utils.py                 # Fonctions utilitaires
│
├── data/                        # Données du système
│   ├── shared_files/            # Fichiers partagés du peer
│   ├── downloads/               # Fichiers téléchargés
│   ├── peer_cache.db            # Cache local du peer (SQLite)
│   ├── peer_id.txt              # Identifiant unique du peer
│   └── tracker.db               # Base de données du tracker (SQLite)
│
├── instance/                    # Instance Flask
│   └── tracker.db               # Base de données du tracker
│
└── logs/                        # Fichiers de logs
    ├── tracker.log              # Logs du tracker
    └── peer1.log                # Logs du peer

```

## Description des Composants

### Tracker
Serveur central qui maintient une liste des peers connectés et des fichiers partagés.
- Port: 5000
- Dashboard: http://localhost:5000
- Base de données: SQLite

### Peer
Client P2P qui partage et télécharge des fichiers.
- Port: 8001 (web), 5001 (P2P)
- Interface: http://localhost:8001
- Fonctionnalités:
  - Upload de fichiers avec configuration des permissions
  - Téléchargement de fichiers depuis le réseau
  - Découverte automatique des peers (UDP)
  - Cache local pour optimiser les recherches
  - Fragmentation des gros fichiers

### Shared
Bibliothèque commune utilisée par le tracker et le peer pour assurer la cohérence.

## Démarrage

### Démarrage complet (Tracker + Peer)
```bash
./start.sh
# Puis choisir l'option 2
```

### Redémarrage rapide
```bash
./restart.sh
```

### Arrêt
```bash
./start.sh
# Puis choisir l'option 4
```

## Interfaces Web

- **Tracker Dashboard**: http://localhost:5000
  - Vue d'ensemble du réseau
  - Statistiques globales
  - Liste des peers connectés

- **Peer Interface**: http://localhost:8001
  - **Dashboard**: Vue d'ensemble et statistiques
  - **Mes Fichiers**: Gestion des fichiers partagés
  - **Réseau**: Recherche et téléchargement de fichiers

## Technologies

- **Backend**: Python 3.13, Flask 3.0.0
- **Base de données**: SQLite avec SQLAlchemy
- **Frontend**: Bootstrap 5, Font Awesome 6, jQuery
- **Réseau**: TCP/IP, UDP (découverte), HTTP (API)
- **Cryptographie**: SHA-256 pour les hash de fichiers

## Architecture

Le système utilise une architecture **hybride**:
- **Centralisé** pour la découverte (Tracker)
- **Décentralisé** pour les transferts (P2P direct entre peers)

Cette approche combine les avantages des deux:
- Découverte rapide et fiable via le tracker
- Transferts directs et efficaces en P2P
- Résilience partielle si le tracker est indisponible (découverte UDP)
