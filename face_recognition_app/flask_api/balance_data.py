"""
Quick script to balance training data by reducing excess samples.
This will keep the best-quality samples and remove duplicates.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import queries
from collections import Counter
import numpy as np

def balance_training_data(target_per_person=15, dry_run=True):
    """
    Balance training data by removing excess samples from people with too many.
    
    Parameters:
    -----------
    target_per_person : int
        Target number of samples per person (default: 15)
    dry_run : bool
        If True, only show what would be deleted without actually deleting
    """
    print("=" * 70)
    print("DATA BALANCING TOOL")
    print("=" * 70)
    
    db = queries.get_db_connection()
    
    # Get all training faces with IDs
    db_conn = db.get_connection()
    cursor = db_conn.cursor()
    
    try:
        cursor.execute("""
            SELECT f.id, f.person_id, p.name, f.embedding, f.source_type
            FROM faces f
            JOIN people p ON f.person_id = p.id
            WHERE f.source_type IN ('training', 'unknown_labeled')
            ORDER BY p.name, f.id
        """)
        
        all_faces = cursor.fetchall()
        
        # Group by person
        person_faces = {}
        for face_id, person_id, person_name, embedding, source_type in all_faces:
            if person_name not in person_faces:
                person_faces[person_name] = []
            person_faces[person_name].append({
                'id': face_id,
                'person_id': person_id,
                'embedding': embedding,
                'source_type': source_type
            })
        
        print(f"\n📊 CURRENT DISTRIBUTION:")
        print("-" * 70)
        for person, faces in sorted(person_faces.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(faces)
            excess = max(0, count - target_per_person)
            status = "✅" if excess == 0 else f"❌ (remove {excess})"
            print(f"  {person:20s} [{count:3d}] {status}")
        
        # Identify faces to remove
        faces_to_remove = []
        
        for person, faces in person_faces.items():
            if len(faces) > target_per_person:
                excess = len(faces) - target_per_person
                
                # Keep the first target_per_person faces (usually better quality)
                # Remove the rest
                to_remove = faces[target_per_person:]
                
                for face in to_remove:
                    faces_to_remove.append({
                        'id': face['id'],
                        'person': person,
                        'source_type': face['source_type']
                    })
        
        if not faces_to_remove:
            print(f"\n✅ Data is already balanced! No changes needed.")
            return
        
        print(f"\n🗑️  FACES TO REMOVE: {len(faces_to_remove)}")
        print("-" * 70)
        
        removal_by_person = Counter([f['person'] for f in faces_to_remove])
        for person, count in removal_by_person.items():
            print(f"  {person:20s} - {count} faces")
        
        if dry_run:
            print(f"\n⚠️  DRY RUN MODE - No changes will be made")
            print(f"   To actually remove faces, run:")
            print(f"   python balance_data.py --execute")
        else:
            print(f"\n⚠️  WARNING: This will permanently delete {len(faces_to_remove)} face records!")
            response = input("   Type 'YES' to confirm: ")
            
            if response != 'YES':
                print("   ❌ Cancelled")
                return
            
            # Delete faces
            face_ids = [f['id'] for f in faces_to_remove]
            
            cursor.execute(
                "DELETE FROM faces WHERE id = ANY(%s)",
                (face_ids,)
            )
            db_conn.commit()
            
            print(f"\n✅ Deleted {len(faces_to_remove)} faces")
            print(f"\n📊 NEW DISTRIBUTION:")
            print("-" * 70)
            
            # Re-query to show new distribution
            cursor.execute("""
                SELECT p.name, COUNT(*) as count
                FROM faces f
                JOIN people p ON f.person_id = p.id
                WHERE f.source_type IN ('training', 'unknown_labeled')
                GROUP BY p.name
                ORDER BY count DESC
            """)
            
            for person_name, count in cursor.fetchall():
                print(f"  {person_name:20s} [{count:3d}]")
            
            print(f"\n🔄 NEXT STEPS:")
            print("-" * 70)
            print("  1. Go to UI → Model Management")
            print("  2. Click 'Retrain Model'")
            print("  3. Wait for training to complete")
            print("  4. Check accuracy (should be much better!)")
            print("  5. Activate the new model")
    
    finally:
        cursor.close()
        db.return_connection(db_conn)
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Balance training data')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually delete faces (default is dry-run)')
    parser.add_argument('--target', type=int, default=15,
                       help='Target samples per person (default: 15)')
    
    args = parser.parse_args()
    
    balance_training_data(
        target_per_person=args.target,
        dry_run=not args.execute
    )
