# 🧪 Tests de la Fragmentation Distribuée

## Statut d'Implémentation

### ✅ Phase 1 : Infrastructure (COMPLÉTÉ)
- [x] DistributedChunkManager créé (peer/distributed_chunking.py)
- [x] Nouveaux endpoints API chunks ajoutés (routes.py)
- [x] Modèles mis à jour (FileInfo, DownloadJob)
- [x] Configuration ajoutée (config.yaml)
- [x] Intégration dans PeerApplication

### ⏳ Phase 2 : Tests & Validation (EN COURS)
- [ ] Test 1: Upload fichier < 1GB (comportement normal)
- [ ] Test 2: Upload fichier ≥ 1GB sans peers → Rejet
- [ ] Test 3: Upload fichier ≥ 1GB avec 2+ peers → Distribution
- [ ] Test 4: Vérification chunks sur peers distants
- [ ] Test 5: Download chunks depuis API

### ⏳ Phase 3 : Téléchargement Distribué (À IMPLÉMENTER)
- [ ] Logique de téléchargement multi-peers
- [ ] Assemblage des chunks
- [ ] Gestion partial download
- [ ] Reprise automatique

### ⏳ Phase 4 : Interface Utilisateur (À IMPLÉMENTER)
- [ ] Modal upload avec info distribution
- [ ] Affichage progression par chunk
- [ ] Notifications état peers

---

## 🔧 Préparation des Tests

### 1. Arrêter le Système Actuel
```bash
./stop.sh
```

### 2. Créer un Fichier de Test ≥ 1GB
```bash
# Créer un fichier de 1.5 GB avec dd
dd if=/dev/urandom of=data/shared_files/test_large_1.5GB.bin bs=1M count=1536

# Ou pour un test plus rapide : 100 MB (réduire le seuil à 100MB dans config.yaml)
dd if=/dev/urandom of=data/shared_files/test_100MB.bin bs=1M count=100
```

### 3. Simuler Plusieurs Peers (Temporaire)

Pour tester la distribution, il faut temporairement lancer 2 peers. Créer `config_peer2.yaml`:

```yaml
# Configuration Peer 2 (copie de config.yaml avec modifications)
tracker:
  host: '0.0.0.0'
  port: 5000
  
peer:
  host: '0.0.0.0'
  port_range:
    start: 8001  # Port différent du peer 1
    end: 8100
  shared_folder: 'data/peer2_shared_files'  # Dossier différent
  download_folder: 'data/peer2_downloads'
  cache_database: 'data/peer2_cache.db'
  
  scanner:
    auto_scan_interval: 30
    watch_changes: true
  
  sync:
    interval: 300
    retry_connection: 30

discovery:
  enabled: true
  broadcast_port: 5555
  broadcast_interval: 30
  peer_timeout: 60
  multicast_group: '224.0.0.1'

chunking:
  enabled: true
  threshold_size: 10485760
  chunk_size: 10485760  # 10 MB par chunk
  max_concurrent_chunks: 5
  min_file_size_for_distribution: 1073741824  # 1 GB
  min_peers_for_distribution: 2
  distribution_strategy: 'round_robin'
  auto_resume_downloads: true
  resume_check_interval: 30

limits:
  max_file_size: 5368709120
  max_peers: 100
  max_concurrent_downloads: 5
  max_download_speed: 0

security:
  hash_algorithm: 'sha256'

logging:
  level: 'INFO'
  file: 'logs/peer2.log'

web:
  theme: 'light'
  items_per_page: 20
  auto_refresh_interval: 5000
```

### 4. Script de Lancement Multiple Peers

Créer `test_distributed.sh`:
```bash
#!/bin/bash

echo "🧪 Test de fragmentation distribuée"
echo "===================================="

# 1. Démarrer le tracker
echo "1️⃣ Démarrage du tracker..."
python -m tracker.app &
TRACKER_PID=$!
echo "   Tracker PID: $TRACKER_PID"
sleep 3

# 2. Démarrer le peer 1 (principal)
echo "2️⃣ Démarrage du peer 1..."
python -m peer.app &
PEER1_PID=$!
echo "   Peer 1 PID: $PEER1_PID"
sleep 3

# 3. Démarrer le peer 2 (test)
echo "3️⃣ Démarrage du peer 2..."
python -m peer.app --config config_peer2.yaml &
PEER2_PID=$!
echo "   Peer 2 PID: $PEER2_PID"
sleep 3

echo ""
echo "✅ Système démarré !"
echo "   Tracker: http://localhost:5000"
echo "   Peer 1:  http://localhost:8001"
echo "   Peer 2:  http://localhost:8002 (ou suivant)"
echo ""
echo "🛑 Pour arrêter : kill $TRACKER_PID $PEER1_PID $PEER2_PID"
echo ""
echo "PIDs: $TRACKER_PID,$PEER1_PID,$PEER2_PID" > /tmp/distributed_test.pids
```

---

## 🧪 Scénarios de Test

### Test 1 : Upload Fichier Normal (< 1GB)

**Objectif**: Vérifier que le comportement normal n'est pas affecté

**Étapes**:
1. Créer fichier 50 MB : `dd if=/dev/zero of=data/shared_files/normal_50MB.bin bs=1M count=50`
2. Via l'interface web → "Mes Fichiers" → Upload
3. Vérifier upload réussi sans distribution

**Résultat Attendu**:
- ✅ Upload réussi
- ✅ Fichier visible dans la liste
- ✅ `is_distributed = False`

---

### Test 2 : Upload Fichier ≥ 1GB Sans Peers

**Objectif**: Vérifier le rejet quand pas assez de peers

**Étapes**:
1. S'assurer qu'aucun autre peer n'est connecté (seulement peer 1)
2. Créer fichier 1.5 GB (ou temporairement réduire seuil à 100MB dans config)
3. Tenter upload via interface web

**Résultat Attendu**:
- ❌ Upload rejeté
- ℹ️ Message : "Impossible d'uploader ce fichier (1.5 GB). Distribution requise mais seulement 0 peer(s) disponible(s). Minimum requis : 2 peers."

**Test API Direct**:
```bash
curl -X POST http://localhost:8001/api/files/upload \
  -F "files=@data/shared_files/test_1.5GB.bin" \
  -v
```

**Réponse Attendue**:
```json
{
  "success": false,
  "error": "distribution_required",
  "message": "Impossible d'uploader ce fichier (1.50 GB)...",
  "file_size_gb": 1.5,
  "available_peers": 0
}
```

---

### Test 3 : Upload Fichier ≥ 1GB Avec 2+ Peers

**Objectif**: Vérifier la distribution automatique

**Pré-requis**: Lancer tracker + peer1 + peer2

**Étapes**:
1. Vérifier 2 peers connectés via Dashboard
2. Upload fichier 1.5 GB via peer1
3. Observer les logs des deux peers
4. Vérifier la distribution dans la BDD

**Résultat Attendu**:
- ✅ Upload accepté
- ✅ Fichier fragmenté en ~146 chunks (1.5GB / 10MB)
- ✅ Chunks répartis équitablement :
  - Peer 1 : ~49 chunks
  - Peer 2 : ~49 chunks
  - Peer 1 : ~48 chunks (round-robin)
- ✅ Métadonnées sauvegardées avec `distribution_map`

**Vérification dans les Logs**:
```
# Peer 1
INFO - Distribution du fichier test_1.5GB.bin (1.50 GB)
INFO - Chunks distribués: {peer1: [0,2,4...], peer2: [1,3,5...]}
INFO - Distribution terminée: 73/146 chunks envoyés

# Peer 2
INFO - Chunk 1 du fichier abc123... stocké localement (10485760 octets)
INFO - Chunk 3 du fichier abc123... stocké localement (10485760 octets)
...
```

**Vérification Filesystem**:
```bash
# Peer 2 devrait avoir reçu ~73 chunks
ls -lh data/peer2_downloads/distributed_chunks/<file_id>/

# Exemple sortie:
chunk_1.bin   10M
chunk_1.hash  64B
chunk_3.bin   10M
chunk_3.hash  64B
...
```

---

### Test 4 : Récupération Chunk via API

**Objectif**: Vérifier l'endpoint GET /api/chunks/<file_id>/<chunk_index>

**Étapes**:
1. Après Test 3, identifier le file_id du fichier distribué
2. Demander un chunk stocké sur peer2

**Commande**:
```bash
# Obtenir le file_id
FILE_ID=$(curl -s http://localhost:8001/api/cache/files | jq -r '.files[] | select(.name | contains("1.5GB")) | .id')

# Demander chunk 1 depuis peer2
curl -X GET "http://localhost:8002/api/chunks/$FILE_ID/1" \
  --output /tmp/chunk_1_test.bin

# Vérifier la taille (devrait être 10MB)
ls -lh /tmp/chunk_1_test.bin
```

**Résultat Attendu**:
- ✅ Fichier chunk_1_test.bin de 10 MB téléchargé
- ✅ Status HTTP 200

---

### Test 5 : Stockage Chunk via API

**Objectif**: Vérifier l'endpoint POST /api/chunks/store

**Commande**:
```bash
# Créer un chunk de test
dd if=/dev/urandom of=/tmp/test_chunk.bin bs=1M count=10

# Calculer le hash
HASH=$(sha256sum /tmp/test_chunk.bin | awk '{print $1}')

# Envoyer au peer 1
curl -X POST http://localhost:8001/api/chunks/store \
  -F "file_id=test-file-123" \
  -F "chunk_index=5" \
  -F "chunk_hash=$HASH" \
  -F "chunk_data=@/tmp/test_chunk.bin" \
  -v
```

**Résultat Attendu**:
```json
{
  "success": true,
  "message": "Chunk 5 stocké",
  "chunk_index": 5,
  "size": 10485760
}
```

**Vérification**:
```bash
# Le chunk devrait être stocké localement
ls -lh data/downloads/distributed_chunks/test-file-123/
# chunk_5.bin   10M
# chunk_5.hash  64B
```

---

## 🐛 Debugging

### Vérifier les Peers Connectés
```bash
curl -s http://localhost:5000/api/peers | jq '.peers[] | {id, name, status}'
```

### Vérifier les Fichiers Distribués
```bash
curl -s http://localhost:8001/api/cache/files | jq '.files[] | select(.is_distributed == true)'
```

### Monitorer les Logs en Temps Réel
```bash
# Terminal 1: Tracker
tail -f logs/tracker.log

# Terminal 2: Peer 1
tail -f logs/app.log

# Terminal 3: Peer 2
tail -f logs/peer2.log
```

### Tester la Distribution Manuellement (Python)
```python
# test_distribution.py
import requests
import json

# 1. Vérifier peers disponibles
resp = requests.get('http://localhost:8001/api/stats')
stats = resp.json()
print(f"Peers disponibles: {stats['statistics']['network']['connected_peers']}")

# 2. Simuler can_distribute
file_size_gb = 1.5
can_dist = file_size_gb >= 1.0  # Seuil 1 GB
peers_available = stats['statistics']['network']['connected_peers']
can_upload = can_dist and peers_available >= 2

print(f"Peut uploader fichier {file_size_gb}GB ? {can_upload}")
print(f"Raison: {peers_available} peers disponibles (min: 2)")
```

---

## 📊 Métriques de Succès

### Test 1 (Upload Normal)
- [x] Upload < 1GB fonctionne
- [x] Pas de fragmentation distribuée
- [x] Temps upload < 5s pour 50MB

### Test 2 (Rejet Sans Peers)
- [x] Upload ≥ 1GB bloqué
- [x] Message d'erreur clair
- [x] HTTP 400 avec error: "distribution_required"

### Test 3 (Distribution Réussie)
- [x] Chunks répartis équitablement
- [x] Au moins 50% des chunks envoyés avec succès
- [x] Métadonnées distribution_map correctes
- [x] Logs montrent les transferts

### Test 4 (Récupération Chunk)
- [x] HTTP 200
- [x] Taille fichier = chunk_size
- [x] Hash valide

### Test 5 (Stockage Chunk)
- [x] HTTP 200
- [x] Chunk stocké dans distributed_chunks/
- [x] Hash sauvegardé

---

## 🚀 Prochaines Étapes

1. **Phase 2 Actuelle** : Exécuter les tests 1-5 ci-dessus
2. **Phase 3** : Implémenter le téléchargement distribué
   - Modifier `peer_client.py` pour télécharger depuis plusieurs peers
   - Assembler les chunks avec `chunk_manager.write_chunk()`
   - Gérer les peers offline (partial download)
3. **Phase 4** : Interface utilisateur
   - Modal upload avec info distribution
   - Barre de progression par chunk
   - Liste des peers et statut
4. **Phase 5** : Optimisations
   - Compression des chunks
   - Réplication pour redondance
   - Équilibrage de charge intelligent

---

## 📞 Support

En cas de problème :
1. Vérifier les logs : `logs/app.log`, `logs/peer2.log`, `logs/tracker.log`
2. Vérifier les processus : `ps aux | grep python`
3. Vérifier les ports : `netstat -tulpn | grep -E '5000|8001|8002'`
4. Nettoyer et redémarrer : `./stop.sh && rm -rf data/*.db && ./start.sh`
