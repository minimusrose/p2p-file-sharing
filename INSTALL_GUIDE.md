# 🚀 Installation Rapide - P2P File Sharing

## 📦 Téléchargement

Téléchargez le script correspondant à votre système d'exploitation :

- **Windows** : `run_p2p_windows.bat`
- **Linux/macOS** : `run_p2p_linux.sh`

## 🖥️ Installation Windows

### Prérequis
- Windows 7/8/10/11
- Python 3.8+ ([Télécharger Python](https://www.python.org/downloads/))
  - ⚠️ **Important** : Cochez "Add Python to PATH" lors de l'installation

### Étapes

1. **Téléchargez** `run_p2p_windows.bat`
2. **Double-cliquez** sur le fichier
3. **Suivez** les instructions à l'écran :
   - Choisissez le mode (Tracker + Peer ou Peer seul)
   - Configurez les ports
4. **Terminé !** L'interface web s'ouvre automatiquement

### Utilisation

```batch
# Démarrer
run_p2p_windows.bat

# Arrêter
stop_p2p.bat

# Redémarrer
restart_p2p.bat
```

## 🐧 Installation Linux/macOS

### Prérequis
- Linux (Ubuntu, Debian, Fedora, Arch...) ou macOS
- Python 3.8+ (généralement préinstallé)
- Git (optionnel, pour télécharger le code)

### Étapes

1. **Téléchargez** `run_p2p_linux.sh`

2. **Rendez-le exécutable** :
   ```bash
   chmod +x run_p2p_linux.sh
   ```

3. **Lancez-le** :
   ```bash
   ./run_p2p_linux.sh
   ```

4. **Suivez** les instructions à l'écran

### Utilisation

```bash
# Démarrer
./run_p2p_linux.sh

# Arrêter
./stop_p2p.sh

# Redémarrer
./restart_p2p.sh

# Voir les logs
tail -f ~/.p2p_file_sharing/logs/peer.log
```

## 📁 Structure des fichiers

Après installation, les fichiers sont organisés ainsi :

### Windows
```
C:\Users\VotreNom\.p2p_file_sharing\
├── data/
│   ├── shared_files/     ← Placez vos fichiers à partager ici
│   └── downloads/        ← Fichiers téléchargés
├── logs/
│   ├── tracker.log
│   └── peer.log
├── venv/                 ← Environnement Python
├── run_p2p_windows.bat
├── stop_p2p.bat
└── restart_p2p.bat
```

### Linux/macOS
```
~/.p2p_file_sharing/
├── data/
│   ├── shared_files/     ← Placez vos fichiers à partager ici
│   └── downloads/        ← Fichiers téléchargés
├── logs/
│   ├── tracker.log
│   └── peer.log
├── venv/                 ← Environnement Python
├── run_p2p_linux.sh
├── stop_p2p.sh
└── restart_p2p.sh
```

## 🌐 Accès aux interfaces

### Mode Complet (Tracker + Peer)
- **Tracker Dashboard** : http://localhost:5000
- **Peer Interface** : http://localhost:8001

### Mode Peer uniquement
- **Peer Interface** : http://localhost:8001

## 🔧 Configuration

### Changer les ports

Éditez le script avant de l'exécuter et modifiez :
- `TRACKER_PORT=5000` (pour le tracker)
- `PEER_PORT=8001` (pour le peer)

### Se connecter à un tracker distant

En mode "Peer uniquement", entrez l'URL du tracker :
```
http://adresse-ip-du-tracker:5000
```

## 📊 Partager des fichiers

1. Placez vos fichiers dans :
   - **Windows** : `C:\Users\VotreNom\.p2p_file_sharing\data\shared_files\`
   - **Linux/macOS** : `~/.p2p_file_sharing/data/shared_files/`

2. Ils seront automatiquement détectés et partagés sur le réseau

3. Accédez à l'interface web pour voir vos fichiers partagés

## 🔍 Rechercher et télécharger

1. Ouvrez l'interface web du peer
2. Utilisez la recherche pour trouver des fichiers
3. Cliquez sur "Télécharger"
4. Les fichiers sont sauvegardés dans le dossier `downloads`

## ❓ Problèmes courants

### "Python n'est pas reconnu..."
- **Windows** : Réinstallez Python en cochant "Add Python to PATH"
- **Linux** : `sudo apt install python3` (Ubuntu/Debian)

### Le peer ne démarre pas
- Vérifiez que le port n'est pas déjà utilisé
- Consultez les logs : `logs/peer.log`

### Impossible de se connecter au tracker
- Vérifiez que le tracker est bien démarré
- Vérifiez l'URL du tracker
- Vérifiez le pare-feu

### Les fichiers n'apparaissent pas
- Vérifiez que les fichiers sont bien dans `data/shared_files/`
- Attendez le scan automatique (30 secondes)
- Consultez les logs

## 🛡️ Sécurité

- **Pare-feu** : Autorisez les ports utilisés (par défaut 5000 et 8001)
- **Fichiers privés** : Utilisez l'option "Fichier privé" dans l'interface
- **Réseau local** : Par défaut, accessible uniquement en local
- **Réseau public** : Configuration avancée nécessaire (port forwarding, etc.)

## 📞 Support

- **Documentation** : https://github.com/VOTRE-REPO/wiki
- **Issues** : https://github.com/VOTRE-REPO/issues
- **Discord** : [Lien Discord]

## 📝 Licence

MIT License - Voir le fichier LICENSE pour plus de détails

---

**Bon partage ! 🚀**
