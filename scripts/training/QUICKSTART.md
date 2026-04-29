# Quick Start Guide

Get started with the API-Based Training Script in 5 minutes!

## Prerequisites

- Python 3.8+
- Flask API running at http://localhost:5001
- Training data organized in folders

## Installation

```bash
cd scripts/training
pip install -r requirements.txt
```

## Basic Usage

### 1. Prepare Training Data

Organize your images:

```
training_data/training_data/
├── john/
│   ├── photo1.jpg
│   └── photo2.jpg
├── jane/
│   ├── image1.jpg
│   └── image2.jpg
└── bob/
    ├── face1.jpg
    └── face2.jpg
```

**Requirements:**
- Minimum 2 people
- Minimum 2 images per person
- Supported: .jpg, .jpeg, .png, .bmp, .webp

### 2. Start Flask API

```bash
cd face_recognition_app/flask_api
python app.py
```

### 3. Run Training

```bash
cd scripts/training
python api_training_script.py
```

That's it! The script will:
1. ✓ Check API availability
2. ✓ Discover training images
3. ✓ Upload images through API
4. ✓ Label images
5. ✓ Trigger model retraining
6. ✓ Display training summary

## Advanced Usage

### Custom Training Data Directory

```bash
python api_training_script.py --training-data-dir /path/to/data
```

### Verbose Logging

```bash
python api_training_script.py --verbose
```

### Export Model for Migration

```bash
python api_training_script.py --export-model
```

Creates: `exports/model_export_YYYYMMDD_HHMMSS.zip`

### Create Complete Migration Package

```bash
# Set DATABASE_URL first
export DATABASE_URL=postgresql://admin:admin@localhost:5432/face_recognition

python api_training_script.py --create-migration-package
```

Creates: `exports/migration_package_YYYYMMDD_HHMMSS.tar.gz`

### Import Model on Another Machine

```bash
python api_training_script.py --import-model exports/model_export_20250128_143022.zip
```

## Environment Configuration

Create `.env` file (optional):

```bash
# .env
FLASK_API_URL=http://localhost:5001
DATABASE_URL=postgresql://admin:admin@localhost:5432/face_recognition
```

## Troubleshooting

### API Not Available

**Error:** `Flask API is not available`

**Fix:**
```bash
# Start Flask API
cd face_recognition_app/flask_api
python app.py
```

### No Training Data

**Error:** `No person directories found`

**Fix:**
- Check path: `--training-data-dir training_data/training_data`
- Ensure person subfolders exist
- Verify image file formats

### Image Upload Failures

**Error:** `No face detected`

**Fix:**
- Use clear, well-lit photos
- Ensure exactly one face per image
- Remove group photos

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [MIGRATION.md](exports/MIGRATION.md) for deployment guides
- Review training summary for model metrics

## Support

For issues, check:
- Flask API logs
- Training script verbose output: `--verbose`
- Main project documentation

## Example Output

```
================================================================================
  API-BASED MODEL TRAINING
================================================================================

[Step 1] Checking API availability...
✓ API is available

[Step 2] Discovering training data...
✓ Found 3 persons with 6 total images
  - john: 2 images
  - jane: 2 images
  - bob: 2 images

[Step 3] Validating minimum requirements...
✓ Minimum requirements met

[Step 4] Uploading images...
  Processing john...
  [1/6] Uploading photo1.jpg... ✓
  [2/6] Uploading photo2.jpg... ✓
  ...
✓ Successfully uploaded 6/6 images

[Step 5] Labeling images...
  [1/6] Labeling photo1.jpg as john... ✓
  ...
✓ Successfully labeled 6/6 images

[Step 6] Triggering model retraining...
✓ Retraining job started (job_id: abc123)

[Step 7] Waiting for training to complete...
  [0%] Queued
  [50%] Training in progress...
  [100%] Training in progress...
  ✓ Training completed successfully!

================================================================================
  TRAINING SUMMARY
================================================================================

✓ Training completed successfully!
  Execution time: 2m 15s

  Image Processing:
    - Total images processed: 6
    - Successful uploads: 6
    - Successful labels: 6
    - Failed images: 0

  Persons Trained: 3
    - john: 2/2 images
    - jane: 2/2 images
    - bob: 2/2 images

  Model Metrics:
    - Cross-Validation Accuracy: 95.50%
    - Number of Classes: 3
    - Model Version: v1

================================================================================

Next steps:
  1. The new model is now active in the Flask API
  2. Test face recognition with your images/videos
  3. Use --export-model to create a migration package
```
