# How to Run Bulk Training Tool

## Fixed Issues
✅ DatabaseConnection class recreated  
✅ Import errors resolved  
✅ Model storage bug fixed  
✅ Multiple images per person bug fixed  

## Quick Start

### From Project Root Directory

You should run the training from the **project root** directory (where you see `face_recognition_app/`, `training_data/`, etc.):

```bash
# Check you're in the right directory
pwd
# Should show: C:\Pesonal\AIML\CapStonProject\FaceRecornization

# Run training with default path
python face_recognition_app/bulk_training_tool/bulk_train.py

# OR run with verbose output
python face_recognition_app/bulk_training_tool/bulk_train.py --verbose

# OR specify custom training data path
python face_recognition_app/bulk_training_tool/bulk_train.py --training-data-dir training_data/training_data --verbose
```

### ❌ Don't Do This
```bash
# DON'T cd into bulk_training_tool first
cd face_recognition_app/bulk_training_tool  # ❌ Wrong!
python bulk_train.py  # ❌ Will fail!
```

### ✅ Do This Instead
```bash
# Stay in project root
python face_recognition_app/bulk_training_tool/bulk_train.py  # ✅ Correct!
```

## Verify After Training

After training completes, verify everything worked:

```bash
python face_recognition_app/bulk_training_tool/verify_model_storage.py
```

## Expected Output

```
================================================================================
  BULK TRAINING TOOL
================================================================================

[Step 1] Initializing database connection
✓ Database connected

[Step 2] Discovering training data
✓ Found 3 persons with 30 total images
  - John: 10 images
  - Jane: 8 images
  - Bob: 12 images

[Step 3] Validating minimum requirements
✓ Minimum requirements met

[Step 4] Processing and storing images
  Processing John...
  [1/30] Processing john_001.jpg... OK
  [2/30] Processing john_002.jpg... OK
  ...
✓ Successfully processed 30/30 images

[Step 5] Training model
✓ Model training completed

================================================================================
  TRAINING SUMMARY
================================================================================
OK Training completed successfully!

  Model Metrics:
    - Cross-Validation Accuracy: 95.00%
    - Number of Classes: 3
    - Model Version: v1
================================================================================
```

## Troubleshooting

### Error: "Cannot find path"
**Problem:** You're trying to `cd` into the directory first  
**Solution:** Stay in project root and use full path

### Error: "ModuleNotFoundError: No module named 'face_recognition_app'"
**Problem:** You're not in the project root directory  
**Solution:** Navigate to project root first:
```bash
cd C:\Pesonal\AIML\CapStonProject\FaceRecornization
```

### Error: "No module named 'face_recognition_app.database'"
**Problem:** The database module was missing (now fixed)  
**Solution:** The DatabaseConnection class has been recreated

### Error: "Connection refused" or database errors
**Problem:** PostgreSQL database is not running  
**Solution:** Start your PostgreSQL database first

## What's Different Now?

### Before Fixes
- ❌ Only 1 image per person stored
- ❌ Model not saved to database
- ❌ DatabaseConnection class missing

### After Fixes
- ✅ ALL images per person stored
- ✅ Model saved to database
- ✅ DatabaseConnection class recreated
- ✅ 10-30x more training data
- ✅ Much better accuracy

## Next Steps

1. Run training from project root
2. Verify with verification script
3. Check model in UI
4. Test face recognition

All fixes are backward compatible - no UI or API changes needed!
