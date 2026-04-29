"""
Script to help improve model performance by providing actionable steps.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import queries
from collections import Counter

def main():
    print("=" * 70)
    print("MODEL IMPROVEMENT GUIDE")
    print("=" * 70)
    
    db = queries.get_db_connection()
    embeddings_data = queries.get_embeddings_for_training(db, include_unknown_labeled=True)
    person_counts = Counter([person_name for _, person_name in embeddings_data])
    
    print("\n📊 CURRENT DATA DISTRIBUTION:")
    print("-" * 70)
    for person, count in sorted(person_counts.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * (count // 2)
        print(f"  {person:20s} [{count:3d}] {bar}")
    
    # Calculate target
    target_per_person = 15  # Recommended minimum
    
    print(f"\n🎯 TARGET: {target_per_person} samples per person")
    print("-" * 70)
    
    needs_more = []
    for person, count in person_counts.items():
        needed = max(0, target_per_person - count)
        if needed > 0:
            needs_more.append((person, count, needed))
            print(f"  {person:20s} has {count:3d}, needs {needed:3d} more ❌")
        else:
            print(f"  {person:20s} has {count:3d}, sufficient ✅")
    
    if needs_more:
        print(f"\n📸 ACTION PLAN:")
        print("-" * 70)
        print("For each person who needs more samples:")
        print()
        print("OPTION 1: Use the Python Real-Time App")
        print("  1. Run: python main.py (in python_realtime_face_recognition/)")
        print("  2. Have the person sit in front of camera")
        print("  3. Let it capture their face multiple times")
        print("  4. Unknown faces are auto-saved to database")
        print("  5. Go to UI → Unknown Faces → Label them")
        print()
        print("OPTION 2: Upload Images via UI")
        print("  1. Take 10-15 photos of each person")
        print("  2. Vary: angles, lighting, expressions, distance")
        print("  3. Go to UI → Training → Upload images")
        print("  4. Label each image with person's name")
        print()
        print("OPTION 3: Use Existing Unknown Faces")
        print("  1. Go to UI → Unknown Faces")
        print("  2. Look for unlabeled faces of these people")
        print("  3. Label them with correct names")
        print()
        
        print("📋 SPECIFIC NEEDS:")
        print("-" * 70)
        for person, current, needed in sorted(needs_more, key=lambda x: x[2], reverse=True):
            print(f"  • {person}: capture {needed} more images")
    
    # Check for people with too many samples
    max_count = max(person_counts.values())
    min_count = min(person_counts.values())
    
    if max_count > min_count * 3:
        print(f"\n⚖️  DATA IMBALANCE DETECTED:")
        print("-" * 70)
        print(f"  Ratio: {max_count}:{min_count} (should be < 3:1)")
        print()
        print("  OPTION A: Add more samples for people with fewer images")
        print("  OPTION B: Remove excess samples from people with too many")
        print()
        print("  To remove excess samples:")
        print("    1. Go to database and query faces table")
        print("    2. Delete some samples for people with 30+ images")
        print("    3. Keep 15-20 samples per person for balance")
    
    print(f"\n🔄 AFTER COLLECTING MORE DATA:")
    print("-" * 70)
    print("  1. Go to UI → Model Management")
    print("  2. Click 'Retrain Model' button")
    print("  3. Wait for training (shows progress)")
    print("  4. Check new model accuracy (should be 80%+)")
    print("  5. Click 'Activate' on the new model")
    print("  6. Test with Python app - you should be recognized!")
    
    print(f"\n💡 PRO TIPS:")
    print("-" * 70)
    print("  • Capture faces in different lighting (bright, dim, natural)")
    print("  • Vary angles (straight, left, right, slightly up/down)")
    print("  • Include different expressions (neutral, smiling)")
    print("  • Vary distance (close-up, medium, far)")
    print("  • Use different backgrounds if possible")
    print("  • Ensure face is clearly visible (no blur, no obstruction)")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
