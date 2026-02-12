"""
Script de migration de la base de données pour ajouter le support des peers web.

Ce script :
1. Sauvegarde l'ancienne base de données
2. La supprime
3. Crée une nouvelle base avec les nouveaux champs (is_web_peer, user_id)
"""

import os
import shutil
from datetime import datetime

def migrate_database():
    """Migration de la base de données"""
    
    # Chemins
    db_path = 'instance/tracker.db'
    backup_dir = 'instance/backups'
    
    # Créer le dossier de backup
    os.makedirs(backup_dir, exist_ok=True)
    
    # Sauvegarder l'ancienne base si elle existe
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'tracker_backup_{timestamp}.db')
        shutil.copy2(db_path, backup_path)
        print(f"✅ Base de données sauvegardée : {backup_path}")
        
        # Supprimer l'ancienne base
        os.remove(db_path)
        print(f"✅ Ancienne base de données supprimée")
    else:
        print("ℹ️  Aucune base de données existante trouvée")
    
    print("\n🔄 Création de la nouvelle base de données...")
    print("   Veuillez démarrer le tracker pour créer la nouvelle base.")
    print("   Les nouveaux champs seront automatiquement ajoutés :")
    print("   - Peer.is_web_peer (Boolean)")
    print("   - Peer.user_id (Integer, Foreign Key)")
    print("\n✅ Migration préparée avec succès !")
    print("   Lancez : python -m tracker.app")

if __name__ == '__main__':
    migrate_database()
