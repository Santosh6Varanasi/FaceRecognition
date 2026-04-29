"""
Diagnostic script to analyze training data and model performance.
Run this to understand why model accuracy is low.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import queries
import numpy as np
from collections import Counter

def diagnose_training_data():
    """Analyze training data and provide recommendations."""
    print("=" * 70)
    print("MODEL PERFORMANCE DIAGNOSTIC")
    print("=" * 70)
    
    db = queries.get_db_connection()
    
    # Get training data
    print("\n1. Loading training data...")
    embeddings_data = queries.get_embeddings_for_training(db, include_unknown_labeled=True)
    
    if not embeddings_data:
        print("❌ ERROR: No training data found!")
        print("\nRECOMMENDATIONS:")
        print("  1. Label faces through the UI (Unknown Faces page)")
        print("  2. Upload training images (Training page)")
        print("  3. Ensure at least 2 people with 5+ images each")
        return
    
    # Analyze data distribution
    print(f"✅ Found {len(embeddings_data)} total training samples")
    
    person_counts = Counter([person_name for _, person_name in embeddings_data])
    num_people = len(person_counts)
    
    print(f"\n2. Training data distribution:")
    print(f"   Total people: {num_people}")
    print(f"   Samples per person:")
    for person, count in sorted(person_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"     - {person}: {count} samples")
    
    # Check for issues
    print(f"\n3. Checking for common issues...")
    
    issues = []
    warnings = []
    
    # Issue 1: Too few people
    if num_people < 2:
        issues.append("❌ CRITICAL: Need at least 2 people for classification")
    elif num_people < 3:
        warnings.append("⚠️  WARNING: Only 2 people - model may overfit")
    
    # Issue 2: Imbalanced data
    min_samples = min(person_counts.values())
    max_samples = max(person_counts.values())
    
    if min_samples < 2:
        issues.append(f"❌ CRITICAL: Some people have < 2 samples (minimum required)")
    elif min_samples < 5:
        warnings.append(f"⚠️  WARNING: Some people have < 5 samples (recommended minimum)")
    
    if max_samples / min_samples > 5:
        warnings.append(f"⚠️  WARNING: Imbalanced data (ratio {max_samples}:{min_samples})")
    
    # Issue 3: Too few total samples
    if len(embeddings_data) < 10:
        warnings.append(f"⚠️  WARNING: Only {len(embeddings_data)} total samples (recommend 50+)")
    
    # Issue 4: Check embedding quality
    embeddings = np.array([e[0] for e in embeddings_data])
    embedding_norms = np.linalg.norm(embeddings, axis=1)
    
    if np.any(embedding_norms < 0.1):
        warnings.append("⚠️  WARNING: Some embeddings have very low magnitude")
    
    if np.std(embedding_norms) > 1.0:
        warnings.append("⚠️  WARNING: High variance in embedding magnitudes")
    
    # Print issues
    if issues:
        print("\n❌ CRITICAL ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
    
    if not issues and not warnings:
        print("   ✅ No major issues detected")
    
    # Get current model info
    print(f"\n4. Current model status:")
    active_model = queries.get_active_model_version(db)
    
    if active_model:
        print(f"   Active model version: {active_model['version_number']}")
        print(f"   Cross-validation accuracy: {active_model['cross_validation_accuracy']*100:.1f}%")
        print(f"   Number of classes: {active_model['num_classes']}")
        print(f"   Training samples: {active_model['num_training_samples']}")
        print(f"   Trained at: {active_model['trained_at']}")
    else:
        print("   ❌ No active model found")
    
    # Recommendations
    print(f"\n5. RECOMMENDATIONS TO IMPROVE ACCURACY:")
    print("=" * 70)
    
    if num_people < 3:
        print("\n📊 ADD MORE PEOPLE:")
        print("   - Current: {} people".format(num_people))
        print("   - Recommended: 3+ people for better model generalization")
    
    if min_samples < 10:
        print("\n📸 ADD MORE SAMPLES PER PERSON:")
        print("   - Current minimum: {} samples".format(min_samples))
        print("   - Recommended: 10-20 samples per person")
        print("   - Capture different:")
        print("     • Angles (front, left, right)")
        print("     • Lighting conditions")
        print("     • Expressions (neutral, smiling)")
        print("     • Distances from camera")
    
    if max_samples / min_samples > 3:
        print("\n⚖️  BALANCE YOUR DATA:")
        print("   - Some people have many more samples than others")
        print("   - Try to have similar number of samples for each person")
        print("   - Current distribution:")
        for person, count in sorted(person_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"     • {person}: {count} samples")
    
    print("\n🔄 AFTER ADDING MORE DATA:")
    print("   1. Go to Model Management in the UI")
    print("   2. Click 'Retrain Model'")
    print("   3. Wait for training to complete")
    print("   4. Activate the new model version")
    print("   5. Test with the Python app again")
    
    print("\n" + "=" * 70)
    print("EXPECTED ACCURACY RANGES:")
    print("=" * 70)
    print("  • 2 people, 2-5 samples each:   40-60% (POOR)")
    print("  • 2 people, 5-10 samples each:  60-80% (FAIR)")
    print("  • 3+ people, 10+ samples each:  80-95% (GOOD)")
    print("  • 5+ people, 20+ samples each:  90-98% (EXCELLENT)")
    print("=" * 70)


if __name__ == "__main__":
    try:
        diagnose_training_data()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
