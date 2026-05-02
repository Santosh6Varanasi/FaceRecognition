#!/usr/bin/env python3
"""
Verify Model Storage
====================
Quick script to verify that trained models are properly stored in the database
and that multiple face embeddings per person are being stored correctly.

Usage:
    python verify_model_storage.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask_api.db import queries
from datetime import datetime


def verify_model_storage():
    """Check if models are stored in model_versions table"""
    print("\n" + "=" * 80)
    print("  MODEL STORAGE & TRAINING DATA VERIFICATION")
    print("=" * 80)
    
    try:
        # Connect to database
        print("\n[1] Connecting to database...")
        db = queries.get_db_connection()
        print("    ✓ Connected")
        
        # Check faces per person
        print("\n[2] Checking training data (faces per person)...")
        db_conn = db.get_connection()
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT 
                p.name,
                COUNT(f.id) as face_count,
                COUNT(DISTINCT f.image_path) as unique_images,
                f.source_type
            FROM people p
            LEFT JOIN faces f ON p.id = f.person_id
            WHERE f.source_type IN ('training', 'unknown_labeled')
            GROUP BY p.name, f.source_type
            ORDER BY face_count DESC
        """)
        
        face_rows = cursor.fetchall()
        
        if not face_rows:
            print("    ⚠ No training faces found in database")
            print("\n    This means:")
            print("    - No training has been completed yet")
            print("    - Run the bulk training tool first")
        else:
            print(f"    ✓ Found training data for {len(face_rows)} person(s)")
            print("\n    Training Data Summary:")
            print("    " + "-" * 76)
            print(f"    {'Person Name':<30} {'Face Count':<15} {'Unique Images':<15} {'Source'}")
            print("    " + "-" * 76)
            
            total_faces = 0
            single_image_persons = []
            
            for row in face_rows:
                name, face_count, unique_images, source_type = row
                print(f"    {name:<30} {face_count:<15} {unique_images:<15} {source_type}")
                total_faces += face_count
                
                if face_count == 1:
                    single_image_persons.append(name)
            
            print("    " + "-" * 76)
            print(f"    {'TOTAL':<30} {total_faces:<15}")
            print("    " + "-" * 76)
            
            # Warning if only single images per person
            if single_image_persons and len(single_image_persons) == len(face_rows):
                print("\n    ⚠ WARNING: Only 1 face per person detected!")
                print("    This indicates the multiple images bug may still be present.")
                print("    Expected: Multiple faces per person for better accuracy")
                print("\n    Possible causes:")
                print("    - Old training data before the fix")
                print("    - Need to re-run bulk training tool")
                print("    - Database constraint issues")
            elif single_image_persons:
                print(f"\n    ⚠ Note: {len(single_image_persons)} person(s) have only 1 face:")
                for name in single_image_persons[:5]:
                    print(f"      - {name}")
                if len(single_image_persons) > 5:
                    print(f"      ... and {len(single_image_persons) - 5} more")
        
        # Query model_versions table
        print("\n[3] Querying model_versions table...")
        
        cursor.execute("""
            SELECT 
                id,
                version_number,
                num_classes,
                num_training_samples,
                cross_validation_accuracy,
                is_active,
                trained_at,
                training_duration_seconds
            FROM model_versions
            ORDER BY trained_at DESC
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        db.return_connection(db_conn)
        
        if not rows:
            print("    ⚠ No models found in database")
            print("\n    This means:")
            print("    - No training has been completed yet, OR")
            print("    - The bulk training tool is not saving models properly")
            print("\n    Next steps:")
            print("    1. Run the bulk training tool")
            print("    2. Check for any errors during training")
            print("    3. Run this script again to verify")
            return False
        
        print(f"    ✓ Found {len(rows)} model version(s)")
        
        # Display model information
        print("\n[4] Model Versions:")
        print("    " + "-" * 76)
        print(f"    {'ID':<6} {'Ver':<6} {'Classes':<10} {'Samples':<10} {'Accuracy':<12} {'Active':<8} {'Trained At'}")
        print("    " + "-" * 76)
        
        active_model = None
        for row in rows:
            model_id, version, classes, samples, accuracy, is_active, trained_at, duration = row
            
            active_str = "YES" if is_active else "No"
            accuracy_str = f"{accuracy:.2%}" if accuracy else "N/A"
            trained_str = trained_at.strftime("%Y-%m-%d %H:%M") if trained_at else "N/A"
            
            print(f"    {model_id:<6} {version:<6} {classes:<10} {samples:<10} {accuracy_str:<12} {active_str:<8} {trained_str}")
            
            if is_active:
                active_model = row
        
        print("    " + "-" * 76)
        
        # Display active model details
        if active_model:
            print("\n[5] Active Model Details:")
            model_id, version, classes, samples, accuracy, is_active, trained_at, duration = active_model
            print(f"    - Version: v{version}")
            print(f"    - Classes: {classes}")
            print(f"    - Training Samples: {samples}")
            print(f"    - Cross-Validation Accuracy: {accuracy:.2%}")
            print(f"    - Trained At: {trained_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    - Training Duration: {duration:.2f} seconds")
            
            # Check if training samples match face count
            if face_rows and total_faces > 0:
                if samples == total_faces:
                    print(f"\n    ✓ Training samples ({samples}) match face count ({total_faces})")
                elif samples < total_faces:
                    print(f"\n    ℹ Training samples ({samples}) < face count ({total_faces})")
                    print(f"      Model was trained before all faces were added")
                    print(f"      Consider retraining to use all available data")
                else:
                    print(f"\n    ℹ Training samples ({samples}) > face count ({total_faces})")
                    print(f"      Some faces may have been deleted since training")
            
            print("\n    ✓ Model is ready for use in UI and API")
        else:
            print("\n[5] ⚠ No active model found")
            print("    All models are marked as inactive")
        
        print("\n" + "=" * 80)
        print("  VERIFICATION COMPLETE")
        print("=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n    ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_model_storage()
    sys.exit(0 if success else 1)
