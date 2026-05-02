# Bulk Training Tool

Fast and reliable bulk training from `training_data/` folder using direct module imports.

## Features

✅ **Direct Module Import** - No HTTP calls, imports Flask API modules directly  
✅ **Face Detection** - Validates faces using MTCNN  
✅ **Unknown Faces Support** - Stores in database for future labeling via Web UI  
✅ **Known Faces Detection** - Trains SVM classifier for recognition  
✅ **Model Accuracy** - Shows cross-validation metrics  
✅ **Model Versioning** - Stores in database with version number  
✅ **Fast & Reliable** - No network overhead, direct database access  

## Quick Start

### 1. Organize Training Data

```
training_data/
└── training_data/
    ├── Santosh/
    │   ├── photo1.jpg
    │   ├── photo2.jpg
    │   └── photo3.jpg
    ├── John/
    │   ├── photo1.jpg
    │   └── photo2.jpg
    └── Mary/
        ├── photo1.jpg
        └── photo2.jpg
```

### 2. Run Training

```bash
cd face_recognition_app/bulk_training_tool
python bulk_train.py --training-data-dir ../../training_data/training_data
```

### 3. With Verbose Logging

```bash
python bulk_train.py --training-data-dir ../../training_data/training_data --verbose
```

## Output Example

```
================================================================================
  BULK TRAINING TOOL
================================================================================

[Step 1] Initializing database connection
✓ Database connected

[Step 2] Discovering training data
✓ Found 3 persons with 7 total images
  - Santosh: 3 images
  - John: 2 images
  - Mary: 2 images

[Step 3] Validating minimum requirements
✓ Minimum requirements met

[Step 4] Processing and storing images
  Processing Santosh...
  [1/7] Processing photo1.jpg... ✓
  [2/7] Processing photo2.jpg... ✓
  [3/7] Processing photo3.jpg... ✓
  
  Processing John...
  [4/7] Processing photo1.jpg... ✓
  [5/7] Processing photo2.jpg... ✓
  
  Processing Mary...
  [6/7] Processing photo1.jpg... ✓
  [7/7] Processing photo2.jpg... ✓

✓ Successfully processed 7/7 images

[Step 5] Training model
  Initializing model retrainer...
  Loading training data from database...
  Training SVM classifier...
  Evaluating model with cross-validation...
  Saving model to database...
✓ Model training completed

================================================================================
  TRAINING SUMMARY
================================================================================

✓ Training completed successfully!
  Execution time: 1m 45s

  Image Processing:
    - Total images: 7
    - Successful: 7
    - Failed: 0

  Persons Trained: 3
    - Santosh: 3/3 images
    - John: 2/2 images
    - Mary: 2/2 images

  Model Metrics:
    - Cross-Validation Accuracy: 96.43%
    - Number of Classes: 3
    - Model Version: v8

================================================================================

Next steps:
  1. The new model is now active
  2. Test with webcam: python_realtime_face_recognition/main.py
  3. Test with videos via Web UI
================================================================================
```

## Advantages Over API Script

| Feature | API Script | Bulk Training Tool |
|---------|-----------|-------------------|
| **Speed** | Slower (HTTP overhead) | ✅ Faster (direct import) |
| **Reliability** | Network errors possible | ✅ No network issues |
| **Dependencies** | Flask API must be running | ✅ Works standalone |
| **Error Handling** | HTTP timeouts/retries | ✅ Direct exceptions |
| **Debugging** | Harder (network layer) | ✅ Easier (direct calls) |

## Requirements

- Python 3.8+
- PostgreSQL database running
- Flask API modules available (same directory structure)
- Training data organized in person folders

## Troubleshooting

### "No face detected"
- Ensure images have clear, front-facing faces
- Good lighting required
- One person per image
- Face should be at least 100x100 pixels

### "Module not found"
- Run from `face_recognition_app/bulk_training_tool/` directory
- Ensure Flask API modules are in `../flask_api/`

### "Database connection failed"
- Ensure PostgreSQL is running
- Check `.env` file in `flask_api/` directory
- Verify DATABASE_URL is correct

## Architecture

```
bulk_training_tool/
├── bulk_train.py           # Main script
├── modules/
│   ├── data_discovery.py   # Scan training_data folder
│   └── __init__.py
├── utils/
│   ├── logger.py           # Logging utilities
│   ├── validators.py       # Path validation
│   └── __init__.py
├── requirements.txt
└── README.md

Imports from Flask API:
├── flask_api/db/queries.py              # Database operations
├── flask_api/services/image_validator.py # Image validation
├── flask_api/services/model_retrainer.py # Model training
└── flask_api/config.py                   # Configuration
```

## Next Steps

After training:
1. **Test with webcam**: `cd python_realtime_face_recognition && python main.py`
2. **Test with videos**: Upload videos via Web UI
3. **Label unknown faces**: Use Web UI to label and retrain
4. **Monitor accuracy**: Check model versions in Web UI
