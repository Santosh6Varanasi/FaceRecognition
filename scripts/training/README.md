# API-Based Training Script

Train face recognition models by uploading training data through Flask API endpoints instead of direct database access. Supports model and database migration for cross-environment deployment.

## Features

- ✅ **API-First Training**: Upload and label images through REST APIs
- ✅ **Resilient**: Automatic retry with exponential backoff for network errors
- ✅ **Progress Tracking**: Real-time progress display with detailed summaries
- ✅ **Configurable**: Environment-based configuration for different deployments
- 🚧 **Migration Support**: Export/import models and database (coming soon)

## Prerequisites

- Python 3.8 or higher
- Flask API server running (default: http://localhost:5001)
- PostgreSQL database (for migration features)

## Installation

1. Navigate to the training script directory:
```bash
cd scripts/training
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Create `.env` file for configuration:
```bash
# .env
FLASK_API_URL=http://localhost:5001
DATABASE_URL=postgresql://user:password@localhost:5432/face_recognition
```

## Usage

### Basic Training

Train model with default training data directory:

```bash
python api_training_script.py
```

### Custom Training Data Directory

Specify a custom path to training data:

```bash
python api_training_script.py --training-data-dir /path/to/training_data
```

### Verbose Mode

Enable detailed logging:

```bash
python api_training_script.py --verbose
```

### Help

Display all available options:

```bash
python api_training_script.py --help
```

## Training Data Structure

Organize your training images in the following structure:

```
training_data/training_data/
├── person_1/
│   ├── image1.jpg
│   ├── image2.png
│   └── image3.jpeg
├── person_2/
│   ├── photo1.jpg
│   └── photo2.bmp
└── person_3/
    └── face.webp
```

**Requirements:**
- At least 2 person folders
- At least 2 images per person
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_API_URL` | Flask API base URL | `http://localhost:5001` |
| `DATABASE_URL` | PostgreSQL connection string | (required for migration) |

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--training-data-dir PATH` | Path to training data directory |
| `--verbose` | Enable verbose logging |
| `--export-model` | Export trained model (coming soon) |
| `--export-database` | Export database training data (coming soon) |
| `--create-migration-package` | Create complete migration bundle (coming soon) |
| `--import-model PATH` | Import model from export package (coming soon) |
| `--import-database PATH` | Import database from export file (coming soon) |

## Workflow

The script executes the following steps:

1. **API Availability Check**: Verify Flask API is running
2. **Data Discovery**: Scan training data directory for person folders and images
3. **Validation**: Ensure minimum requirements (2 persons, 2 images each)
4. **Image Upload**: Upload each image through `/api/training/upload-image`
5. **Image Labeling**: Assign person names through `/api/training/label-image`
6. **Trigger Retraining**: Start async training job via `/api/training/retrain`
7. **Status Polling**: Monitor training progress until completion
8. **Summary Display**: Show comprehensive training results

## Error Handling

The script handles errors gracefully:

- **Network Errors**: Automatic retry with exponential backoff (up to 3 attempts)
- **Validation Errors**: Skip invalid images and continue with remaining
- **Server Errors**: Log errors and continue processing
- **Fatal Errors**: Display clear error messages and exit

## Troubleshooting

### API Not Available

**Error**: `Flask API is not available`

**Solution**:
1. Ensure Flask API is running: `cd face_recognition_app/flask_api && python app.py`
2. Check `FLASK_API_URL` environment variable
3. Verify network connectivity

### No Training Data Found

**Error**: `No person directories found`

**Solution**:
1. Check training data directory path
2. Ensure person subfolders exist
3. Verify folder permissions

### Insufficient Training Data

**Error**: `At least 2 people required for training`

**Solution**:
1. Add more person folders (minimum 2)
2. Ensure each person has at least 2 images
3. Check image file formats (must be .jpg, .jpeg, .png, .bmp, or .webp)

### Image Upload Failures

**Error**: `No face detected` or `Multiple faces detected`

**Solution**:
1. Ensure images contain exactly one face
2. Use clear, well-lit photos
3. Remove images with multiple people or no faces

## Migration Features (Coming Soon)

### Export Model

Export trained model with metadata:

```bash
python api_training_script.py --export-model
```

Creates: `exports/model_export_YYYYMMDD_HHMMSS.zip`

### Export Database

Export database training data:

```bash
python api_training_script.py --export-database
```

Creates: `exports/database_export_YYYYMMDD_HHMMSS.sql`

### Create Migration Package

Create complete migration bundle:

```bash
python api_training_script.py --create-migration-package
```

Creates: `exports/migration_package_YYYYMMDD_HHMMSS.tar.gz`

### Import Model

Import model from export package:

```bash
python api_training_script.py --import-model exports/model_export_20250128_143022.zip
```

### Import Database

Import database from export file:

```bash
python api_training_script.py --import-database exports/database_export_20250128_143045.sql
```

## Development

### Project Structure

```
scripts/training/
├── api_training_script.py      # Main CLI entry point
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── modules/                     # Core modules
│   ├── __init__.py
│   ├── api_client.py           # HTTP client with retry logic
│   ├── data_discovery.py       # Training data discovery
│   ├── training_orchestrator.py # Workflow orchestration
│   └── migration_manager.py    # Export/import (coming soon)
└── utils/                       # Utility modules
    ├── __init__.py
    ├── logger.py               # Logging utilities
    └── validators.py           # Validation utilities
```

### Running Tests

```bash
pytest
```

## License

Part of the Face Recognition Application project.

## Support

For issues or questions, please refer to the main project documentation.
