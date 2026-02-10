# Spécification Technique : Fragmentation Distribuée

## 📋 Vue d'Ensemble

Système de fragmentation pour fichiers ≥ 1 GB avec distribution des morceaux sur plusieurs peers et téléchargement avec reprise automatique.

## 🎯 Comportement

### Upload d'un Fichier ≥ 1 GB

```
1. Détection de la taille
   ├─ Fichier < 1 GB → Upload normal
   └─ Fichier ≥ 1 GB → Fragmentation distribuée

2. Vérification des peers disponibles
   ├─ Peers disponibles ≥ 2 → Continuer
   └─ Peers disponibles < 2 → Bloquer avec message
   
3. Fragmentation du fichier
   ├─ Diviser en chunks (taille configurable, ex: 10 MB)
   ├─ Calculer hash de chaque chunk
   └─ Créer métadonnées de distribution

4. Distribution des chunks
   ├─ Répartir équitablement entre peers disponibles
   ├─ Garder 1 copie locale (chunk 0 ou métadonnées)
   └─ Envoyer chunks aux autres peers
   
5. Synchronisation avec tracker
   ├─ Enregistrer fichier comme "chunked"
   ├─ Stocker mapping: chunk_index → peer_id
   └─ Marquer comme "distribué"
```

### Téléchargement d'un Fichier Fragmenté

```
1. Récupération des métadonnées
   ├─ Liste des chunks nécessaires
   ├─ Hash de chaque chunk
   └─ Mapping: chunk → peer propriétaire

2. Vérification de disponibilité
   ├─ Tous peers en ligne → Téléchargement complet
   └─ Certains peers hors ligne → Téléchargement partiel

3. Téléchargement parallèle
   ├─ Pour chaque chunk disponible:
   │   ├─ Télécharger depuis peer propriétaire
   │   ├─ Vérifier hash
   │   └─ Écrire dans fichier final
   └─ Mise à jour progression en temps réel

4. Gestion des chunks manquants
   ├─ Marquer chunks comme "en attente"
   ├─ Surveiller retour des peers
   └─ Reprendre automatiquement
   
5. Assemblage final
   ├─ Vérifier tous les chunks
   ├─ Calculer hash global
   └─ Marquer comme "complet"
```

## 🗂️ Structure de Données

### ChunkDistribution (nouvelle classe)
```python
@dataclass
class ChunkDistribution:
    file_id: str
    chunk_index: int
    peer_id: str
    chunk_hash: str
    stored_at: datetime
    is_available: bool
```

### FileInfo (modifications)
```python
class FileInfo:
    # Existant
    is_chunked: bool
    chunk_size: Optional[int]
    chunks_count: Optional[int]
    chunks_hashes: Optional[str]  # JSON array
    
    # Nouveau
    distribution_map: Optional[str]  # JSON: {chunk_index: peer_id}
    is_distributed: bool = False
    minimum_peers_required: int = 2
```

### DownloadJob (modifications)
```python
class DownloadJob:
    # Existant
    chunks_status: Optional[dict]
    
    # Nouveau
    chunks_progress: dict  # {chunk_index: {'status': 'pending'|'downloading'|'completed'|'failed', 'peer_id': str}}
    missing_peers: list  # Liste des peer_id hors ligne
    auto_resume: bool = True
```

## 📁 Fichiers à Modifier/Créer

### 1. peer/distributed_chunking.py (NOUVEAU)
```python
class DistributedChunkManager:
    """Gère la distribution des chunks sur plusieurs peers"""
    
    def should_distribute(self, file_size: int) -> bool:
        """Vérifie si fichier doit être distribué (≥ 1GB)"""
        
    def get_available_peers(self) -> List[PeerInfo]:
        """Récupère les peers disponibles pour distribution"""
        
    def distribute_chunks(self, file_info: FileInfo, chunks_hashes: List[str]) -> dict:
        """Distribue les chunks entre peers disponibles"""
        
    def send_chunk_to_peer(self, peer_id: str, chunk_data: bytes, chunk_index: int):
        """Envoie un chunk à un peer spécifique"""
        
    def receive_chunk(self, file_id: str, chunk_index: int, data: bytes):
        """Reçoit et stocke un chunk d'un autre peer"""
```

### 2. peer/routes.py (MODIFICATIONS)
```python
# Nouveaux endpoints

@peer_bp.route('/api/files/upload', methods=['POST'])
def api_upload_files():
    # Ajouter vérification taille ≥ 1GB
    # Si oui → appeler distribute_chunks()
    
@peer_bp.route('/api/chunks/store', methods=['POST'])
def api_store_chunk():
    """Reçoit un chunk d'un autre peer"""
    
@peer_bp.route('/api/chunks/<file_id>/<int:chunk_index>', methods=['GET'])
def api_get_chunk(file_id, chunk_index):
    """Envoie un chunk à un peer qui le demande"""
    
@peer_bp.route('/api/download/<job_id>/chunks_status')
def api_chunks_status(job_id):
    """Statut détaillé des chunks d'un téléchargement"""
```

### 3. peer/app.py (MODIFICATIONS)
```python
class PeerApplication:
    def __init__(self):
        # Ajouter
        self.distributed_chunk_manager = DistributedChunkManager(...)
    
    def scan_and_distribute_large_file(self, filepath: Path):
        """Traite un nouveau fichier ≥ 1GB"""
```

### 4. tracker/models.py (MODIFICATIONS)
```python
class File(db.Model):
    # Ajouter colonnes
    is_distributed = db.Column(db.Boolean, default=False)
    distribution_map = db.Column(db.Text)  # JSON
    minimum_peers_required = db.Column(db.Integer, default=2)

class ChunkLocation(db.Model):  # NOUVEAU
    id = db.Column(db.String, primary_key=True)
    file_id = db.Column(db.String, db.ForeignKey('file.id'))
    chunk_index = db.Column(db.Integer)
    peer_id = db.Column(db.String, db.ForeignKey('peer.id'))
    chunk_hash = db.Column(db.String)
    stored_at = db.Column(db.DateTime)
```

## 🎨 Interface Utilisateur

### Upload d'un Gros Fichier
```
┌─────────────────────────────────────────────┐
│ 📤 Upload de gros fichier détecté           │
│                                             │
│ Fichier : video_4K.mp4                      │
│ Taille : 2.5 GB                             │
│                                             │
│ ⚠️  Ce fichier nécessite une distribution   │
│     sur plusieurs peers                     │
│                                             │
│ Peers disponibles : 3                       │
│ ✅ Peer A (utilisateur-1)                   │
│ ✅ Peer B (utilisateur-2)                   │
│ ✅ Peer C (utilisateur-3)                   │
│                                             │
│ Distribution :                              │
│ • Chunks 0-83   → Votre ordinateur          │
│ • Chunks 84-167 → Peer A                    │
│ • Chunks 168-251→ Peer B                    │
│                                             │
│ [Continuer] [Annuler]                       │
└─────────────────────────────────────────────┘
```

### Téléchargement Partiel
```
┌─────────────────────────────────────────────┐
│ 📥 Téléchargement : video_4K.mp4            │
│                                             │
│ Progression : 67% (170/252 chunks)          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░     │
│                                             │
│ État des morceaux :                         │
│ ✅ Chunks 0-83   (Votre PC)     - Complet   │
│ ✅ Chunks 84-167 (Peer A)       - Complet   │
│ ⏳ Chunks 168-251 (Peer B)      - En attente│
│                                             │
│ ℹ️  Peer B est hors ligne                   │
│    Reprise automatique activée              │
│                                             │
│ Vitesse : 5.2 MB/s                          │
│ Temps restant : Estimation en attente...    │
│                                             │
│ [Mettre en pause] [Annuler]                 │
└─────────────────────────────────────────────┘
```

## ⚙️ Configuration

### config.yaml
```yaml
chunking:
  chunk_size: 10485760  # 10 MB
  min_file_size_for_distribution: 1073741824  # 1 GB
  min_peers_for_distribution: 2
  distribution_strategy: 'round_robin'  # ou 'balanced'
  auto_resume_downloads: true
  resume_check_interval: 30  # secondes
```

## 🔒 Sécurité

1. **Vérification des chunks** : Hash SHA-256 de chaque chunk
2. **Authentification** : Seuls les peers autorisés peuvent demander des chunks
3. **Intégrité** : Vérification du hash avant assemblage
4. **Chiffrement** : Optionnel pour les chunks sensibles

## 📊 Algorithme de Distribution

### Round Robin (Simple)
```python
def distribute_round_robin(chunks_count, peers):
    distribution = {}
    for i in range(chunks_count):
        peer_index = i % len(peers)
        distribution[i] = peers[peer_index].id
    return distribution
```

### Balanced (Équilibré par capacité)
```python
def distribute_balanced(chunks_count, peers):
    # Prendre en compte l'espace disque disponible
    # et la charge actuelle de chaque peer
    distribution = {}
    # ... logique d'équilibrage
    return distribution
```

## 🚀 Phases d'Implémentation

### Phase 1 : Infrastructure (Priorité: Haute)
- [x] ChunkManager existe déjà
- [ ] Créer DistributedChunkManager
- [ ] Ajouter endpoints API chunks
- [ ] Modifier modèles BDD

### Phase 2 : Upload Distribué (Priorité: Haute)
- [ ] Détection fichiers ≥ 1GB
- [ ] Vérification peers disponibles
- [ ] Distribution des chunks
- [ ] Envoi aux peers

### Phase 3 : Téléchargement Partiel (Priorité: Moyenne)
- [ ] Téléchargement parallèle
- [ ] Gestion chunks manquants
- [ ] Reprise automatique
- [ ] Assemblage final

### Phase 4 : Interface (Priorité: Moyenne)
- [ ] Modal upload gros fichier
- [ ] Affichage progression détaillée
- [ ] Notifications état chunks

### Phase 5 : Optimisations (Priorité: Basse)
- [ ] Cache intelligent
- [ ] Compression des chunks
- [ ] Réplication pour résilience

## 📝 Tests Nécessaires

1. **Upload 1GB** : Fichier divisé correctement
2. **Distribution** : Chunks bien répartis
3. **Téléchargement complet** : Tous peers en ligne
4. **Téléchargement partiel** : 1 peer hors ligne
5. **Reprise** : Peer revient en ligne
6. **Intégrité** : Hash de tous les chunks valides
7. **Erreurs** : Peer déconnecté pendant envoi

---

**Prochaines Actions** :
1. Créer `distributed_chunking.py`
2. Modifier `routes.py` avec nouveaux endpoints
3. Tester avec fichier de 1.5 GB
