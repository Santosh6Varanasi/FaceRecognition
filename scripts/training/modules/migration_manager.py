"""
Migration Manager Module
========================
Handles export and import of models and database training data for cross-environment deployment.
"""

import os
import json
import zipfile
import tarfile
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


class MigrationError(Exception):
    """Exception raised for migration errors"""
    pass


class MigrationManager:
    """
    Manages model and database export/import for cross-environment deployment.
    
    Export Operations:
        - Export model with metadata
        - Export database training data
        - Create complete migration package
    
    Import Operations:
        - Import model from export package
        - Import database from export file
    """
    
    def __init__(self, export_dir: str = "exports", model_dir: str = "face_recognition_app/models"):
        """
        Initialize migration manager.
        
        Args:
            export_dir: Directory for export files
            model_dir: Directory containing model files
        """
        self.export_dir = export_dir
        self.model_dir = model_dir
        
        # Create export directory if it doesn't exist
        os.makedirs(self.export_dir, exist_ok=True)
    
    def _generate_timestamp(self) -> str:
        """
        Generate timestamp for file naming.
        
        Returns:
            Timestamp string in format YYYYMMDD_HHMMSS
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_model_files(self) -> Tuple[str, str, str]:
        """
        Get paths to model files.
        
        Returns:
            Tuple of (model_path, label_encoder_path, metadata_path)
            
        Raises:
            MigrationError: If model files not found
        """
        model_path = os.path.join(self.model_dir, "svm_model.pkl")
        label_encoder_path = os.path.join(self.model_dir, "label_encoder.pkl")
        metadata_path = os.path.join(self.model_dir, "model_metadata.pkl")
        
        if not os.path.exists(model_path):
            raise MigrationError(f"Model file not found: {model_path}")
        
        if not os.path.exists(label_encoder_path):
            raise MigrationError(f"Label encoder file not found: {label_encoder_path}")
        
        return model_path, label_encoder_path, metadata_path

    def export_model(self, training_metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Export trained model with metadata to ZIP archive.
        
        Args:
            training_metadata: Optional training metrics from retraining job
            
        Returns:
            Path to exported model ZIP file
            
        Raises:
            MigrationError: If export fails
        """
        print("\n[Export Model] Creating model export package...")
        
        try:
            # Get model files
            model_path, label_encoder_path, metadata_path = self._get_model_files()
            
            # Generate export filename
            timestamp = self._generate_timestamp()
            export_filename = f"model_export_{timestamp}.zip"
            export_path = os.path.join(self.export_dir, export_filename)
            
            # Load existing metadata if available
            import joblib
            existing_metadata = {}
            if os.path.exists(metadata_path):
                try:
                    existing_metadata = joblib.load(metadata_path)
                except Exception as e:
                    print(f"  ⚠ Warning: Could not load existing metadata: {e}")
            
            # Merge with training metadata
            export_metadata = {
                "export_timestamp": datetime.now().isoformat(),
                "model_file": "svm_model.pkl",
                "label_encoder_file": "label_encoder.pkl",
                "system_version": "2.1.0",
                **existing_metadata
            }
            
            if training_metadata:
                export_metadata.update({
                    "cv_accuracy": training_metadata.get("cv_accuracy"),
                    "num_classes": training_metadata.get("num_classes"),
                    "version_number": training_metadata.get("version_number")
                })
            
            # Create ZIP archive
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add model file
                zipf.write(model_path, arcname="svm_model.pkl")
                print(f"  ✓ Added: svm_model.pkl")
                
                # Add label encoder
                zipf.write(label_encoder_path, arcname="label_encoder.pkl")
                print(f"  ✓ Added: label_encoder.pkl")
                
                # Add metadata as JSON
                metadata_json = json.dumps(export_metadata, indent=2)
                zipf.writestr("metadata.json", metadata_json)
                print(f"  ✓ Added: metadata.json")
            
            # Get file size
            file_size = os.path.getsize(export_path)
            size_mb = file_size / (1024 * 1024)
            
            print(f"\n  ✓ Model export created successfully!")
            print(f"    Path: {export_path}")
            print(f"    Size: {size_mb:.2f} MB")
            
            return export_path
        
        except Exception as e:
            raise MigrationError(f"Model export failed: {str(e)}")

    def export_database(self, database_url: str) -> str:
        """
        Export database training data to SQL dump file.
        
        Args:
            database_url: PostgreSQL connection string
            
        Returns:
            Path to exported SQL file
            
        Raises:
            MigrationError: If export fails
        """
        print("\n[Export Database] Creating database export...")
        
        try:
            from urllib.parse import urlparse
            
            # Parse database URL
            parsed = urlparse(database_url)
            db_host = parsed.hostname or "localhost"
            db_port = parsed.port or 5432
            db_name = (parsed.path or "/face_recognition").lstrip("/")
            db_user = parsed.username or "admin"
            db_password = parsed.password or "admin"
            
            # Generate export filename
            timestamp = self._generate_timestamp()
            export_filename = f"database_export_{timestamp}.sql"
            export_path = os.path.join(self.export_dir, export_filename)
            
            # Set password environment variable for pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            # Build pg_dump command
            # Export persons and faces tables with data
            pg_dump_cmd = [
                'pg_dump',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '--table', 'people',
                '--table', 'faces',
                '--data-only',  # Only data, not schema (schema should exist in target)
                '--inserts',    # Use INSERT statements instead of COPY
                '-f', export_path
            ]
            
            print(f"  Exporting from database: {db_name}@{db_host}:{db_port}")
            print(f"  Tables: people, faces")
            
            # Execute pg_dump
            result = subprocess.run(
                pg_dump_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise MigrationError(f"pg_dump failed: {result.stderr}")
            
            # Get file size
            file_size = os.path.getsize(export_path)
            size_kb = file_size / 1024
            
            print(f"\n  ✓ Database export created successfully!")
            print(f"    Path: {export_path}")
            print(f"    Size: {size_kb:.2f} KB")
            
            return export_path
        
        except subprocess.CalledProcessError as e:
            raise MigrationError(f"Database export failed: {str(e)}")
        except Exception as e:
            raise MigrationError(f"Database export failed: {str(e)}")

    def create_migration_package(
        self, 
        model_export_path: str, 
        database_export_path: Optional[str] = None
    ) -> str:
        """
        Create complete migration package with model, database, and documentation.
        
        Args:
            model_export_path: Path to model export ZIP
            database_export_path: Optional path to database export SQL
            
        Returns:
            Path to migration package TAR.GZ file
            
        Raises:
            MigrationError: If package creation fails
        """
        print("\n[Create Migration Package] Bundling migration package...")
        
        try:
            # Generate package filename
            timestamp = self._generate_timestamp()
            package_filename = f"migration_package_{timestamp}.tar.gz"
            package_path = os.path.join(self.export_dir, package_filename)
            
            # Create temporary directory for package contents
            temp_dir = os.path.join(self.export_dir, f"temp_{timestamp}")
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Copy model export
                model_basename = os.path.basename(model_export_path)
                shutil.copy(model_export_path, os.path.join(temp_dir, model_basename))
                print(f"  ✓ Added: {model_basename}")
                
                # Copy database export if provided
                if database_export_path and os.path.exists(database_export_path):
                    db_basename = os.path.basename(database_export_path)
                    shutil.copy(database_export_path, os.path.join(temp_dir, db_basename))
                    print(f"  ✓ Added: {db_basename}")
                
                # Generate .env.template
                env_template = self._generate_env_template()
                env_template_path = os.path.join(temp_dir, ".env.template")
                with open(env_template_path, 'w') as f:
                    f.write(env_template)
                print(f"  ✓ Added: .env.template")
                
                # Generate MIGRATION.md
                migration_doc = self._generate_migration_documentation()
                migration_doc_path = os.path.join(temp_dir, "MIGRATION.md")
                with open(migration_doc_path, 'w') as f:
                    f.write(migration_doc)
                print(f"  ✓ Added: MIGRATION.md")
                
                # Create TAR.GZ archive
                with tarfile.open(package_path, 'w:gz') as tar:
                    tar.add(temp_dir, arcname=os.path.basename(temp_dir))
                
                # Get file size
                file_size = os.path.getsize(package_path)
                size_mb = file_size / (1024 * 1024)
                
                print(f"\n  ✓ Migration package created successfully!")
                print(f"    Path: {package_path}")
                print(f"    Size: {size_mb:.2f} MB")
                
                # Display checklist
                print(f"\n  Package Contents:")
                print(f"    ✓ Model export ({model_basename})")
                if database_export_path:
                    print(f"    ✓ Database export ({db_basename})")
                print(f"    ✓ Environment template (.env.template)")
                print(f"    ✓ Migration documentation (MIGRATION.md)")
                
                return package_path
            
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        
        except Exception as e:
            raise MigrationError(f"Migration package creation failed: {str(e)}")
    
    def _generate_env_template(self) -> str:
        """Generate .env.template file content"""
        return """# Environment Configuration Template for Face Recognition System

# Flask API Configuration
FLASK_API_URL=http://localhost:5001
FLASK_PORT=5001

# Database Configuration
DATABASE_URL=postgresql://admin:admin@localhost:5432/face_recognition

# Model Configuration
MODEL_DIR=face_recognition_app/models

# Training Data Configuration
TRAINING_DATA_DIR=training_data/training_data

# Unknown Face Images Directory
UNKNOWN_FACE_IMAGES_DIR=face_recognition_app/unknown_faces

# Cloud Deployment (AWS Example)
# FLASK_API_URL=https://your-api.amazonaws.com
# DATABASE_URL=postgresql://user:pass@your-rds-endpoint:5432/face_recognition

# Cloud Deployment (Azure Example)
# FLASK_API_URL=https://your-app.azurewebsites.net
# DATABASE_URL=postgresql://user:pass@your-postgres.postgres.database.azure.com:5432/face_recognition

# Cloud Deployment (GCP Example)
# FLASK_API_URL=https://your-app.run.app
# DATABASE_URL=postgresql://user:pass@/face_recognition?host=/cloudsql/project:region:instance
"""
    
    def _generate_migration_documentation(self) -> str:
        """Generate MIGRATION.md file content"""
        return """# Face Recognition System Migration Guide

This guide provides step-by-step instructions for migrating the face recognition system between environments.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- pg_dump and pg_restore utilities (included with PostgreSQL)
- Network access to target environment

## Package Contents

- **model_export_*.zip**: Trained model files and metadata
- **database_export_*.sql**: Database training data (people and faces tables)
- **.env.template**: Environment configuration template
- **MIGRATION.md**: This documentation

## Local-to-Local Migration

### Step 1: Prepare Target Environment

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create PostgreSQL database:
```bash
createdb face_recognition
psql face_recognition < face_recognition_app/database/CREATE_ALL_FRESH.sql
```

3. Configure environment variables:
```bash
cp .env.template .env
# Edit .env with your local configuration
```

### Step 2: Import Model

```bash
python scripts/training/api_training_script.py --import-model model_export_YYYYMMDD_HHMMSS.zip
```

### Step 3: Import Database (Optional)

```bash
python scripts/training/api_training_script.py --import-database database_export_YYYYMMDD_HHMMSS.sql
```

### Step 4: Verify Installation

```bash
# Start Flask API
cd face_recognition_app/flask_api
python app.py

# Test API
curl http://localhost:5001/api/health
```

## Local-to-Cloud Migration

### AWS Deployment

#### Step 1: Set Up AWS Resources

1. **Create RDS PostgreSQL Instance**:
   - Engine: PostgreSQL 12+
   - Instance class: db.t3.micro (or larger)
   - Storage: 20 GB minimum
   - Enable public accessibility (or use VPC)

2. **Create EC2 Instance or Elastic Beanstalk**:
   - AMI: Amazon Linux 2 or Ubuntu 20.04
   - Instance type: t3.medium (or larger)
   - Security groups: Allow HTTP/HTTPS and PostgreSQL

3. **Configure Security Groups**:
   - Allow inbound PostgreSQL (5432) from EC2 to RDS
   - Allow inbound HTTP (80) and HTTPS (443) to EC2

#### Step 2: Deploy Application

1. SSH into EC2 instance:
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

2. Install dependencies:
```bash
sudo yum update -y
sudo yum install python3 postgresql -y
pip3 install -r requirements.txt
```

3. Configure environment:
```bash
export DATABASE_URL=postgresql://user:pass@your-rds-endpoint:5432/face_recognition
export FLASK_API_URL=http://your-ec2-ip:5001
```

4. Import model and database:
```bash
python3 scripts/training/api_training_script.py --import-model model_export_*.zip
python3 scripts/training/api_training_script.py --import-database database_export_*.sql
```

5. Start Flask API:
```bash
cd face_recognition_app/flask_api
python3 app.py
```

### Azure Deployment

#### Step 1: Set Up Azure Resources

1. **Create Azure Database for PostgreSQL**:
```bash
az postgres server create --resource-group myResourceGroup \\
  --name mypostgresserver --location westus \\
  --admin-user myadmin --admin-password <password> \\
  --sku-name B_Gen5_1
```

2. **Create Azure App Service**:
```bash
az webapp create --resource-group myResourceGroup \\
  --plan myAppServicePlan --name myFaceRecognitionApp \\
  --runtime "PYTHON|3.9"
```

#### Step 2: Deploy and Import

1. Configure connection string:
```bash
az webapp config appsettings set --resource-group myResourceGroup \\
  --name myFaceRecognitionApp \\
  --settings DATABASE_URL="postgresql://user:pass@mypostgresserver.postgres.database.azure.com:5432/face_recognition"
```

2. Deploy application and import model/database using Azure CLI or portal.

### GCP Deployment

#### Step 1: Set Up GCP Resources

1. **Create Cloud SQL PostgreSQL Instance**:
```bash
gcloud sql instances create mypostgres --database-version=POSTGRES_13 \\
  --tier=db-f1-micro --region=us-central1
```

2. **Create App Engine or Cloud Run Service**:
```bash
gcloud run deploy face-recognition-api --image gcr.io/project/image \\
  --platform managed --region us-central1
```

#### Step 2: Deploy and Import

1. Configure environment variables in Cloud Run/App Engine
2. Import model and database using Cloud Shell or local machine with gcloud CLI

## Cloud-to-Local Migration

### Step 1: Export from Cloud

1. SSH into cloud instance or use cloud shell
2. Run export commands:
```bash
python scripts/training/api_training_script.py --create-migration-package
```

3. Download migration package:
```bash
scp user@cloud-ip:exports/migration_package_*.tar.gz ./
```

### Step 2: Import to Local

Follow "Local-to-Local Migration" steps above.

## Rollback Procedures

### Model Rollback

If the imported model has issues:

1. Stop Flask API
2. Restore previous model files from backup:
```bash
cp face_recognition_app/models/backup/* face_recognition_app/models/
```
3. Restart Flask API

### Database Rollback

If database import fails or causes issues:

1. Drop and recreate database:
```bash
dropdb face_recognition
createdb face_recognition
psql face_recognition < face_recognition_app/database/CREATE_ALL_FRESH.sql
```

2. Restore from previous backup:
```bash
psql face_recognition < backup/database_export_previous.sql
```

## Troubleshooting

### Model Import Fails

**Error**: "Model file not found" or "Invalid model format"

**Solution**:
- Verify ZIP file is not corrupted
- Check model directory permissions
- Ensure compatible Python version (3.8+)

### Database Import Fails

**Error**: "Connection refused" or "Authentication failed"

**Solution**:
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Verify user has CREATE/INSERT permissions
- Check firewall rules allow PostgreSQL connections

### API Not Responding After Migration

**Error**: API returns 500 errors or doesn't start

**Solution**:
- Check Flask logs for errors
- Verify all environment variables are set
- Ensure model files are in correct directory
- Verify database connection is working

### Performance Issues After Migration

**Symptoms**: Slow response times, high CPU usage

**Solution**:
- Check database indexes are created
- Verify sufficient memory for model loading
- Monitor database connection pool
- Consider upgrading instance size

## Security Considerations

- **Never commit .env files** with real credentials to version control
- **Use SSL/TLS** for database connections in production
- **Rotate credentials** after migration
- **Restrict database access** to application IP addresses only
- **Encrypt migration packages** when transferring over networks

## Support

For additional help, refer to:
- Main project README.md
- Flask API documentation
- Database schema documentation (DATABASE.md)
- Architecture documentation (ARCHITECTURE.md)
"""

    def import_model(self, model_export_path: str) -> Dict[str, Any]:
        """
        Import model from export package.
        
        Args:
            model_export_path: Path to model export ZIP file
            
        Returns:
            Dictionary with import results and metadata
            
        Raises:
            MigrationError: If import fails
        """
        print("\n[Import Model] Importing model from export package...")
        
        try:
            # Validate ZIP file exists
            if not os.path.exists(model_export_path):
                raise MigrationError(f"Model export file not found: {model_export_path}")
            
            # Create temporary extraction directory
            temp_dir = os.path.join(self.export_dir, "temp_import")
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # Extract ZIP file
                print(f"  Extracting: {os.path.basename(model_export_path)}")
                with zipfile.ZipFile(model_export_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # Validate required files exist
                model_file = os.path.join(temp_dir, "svm_model.pkl")
                label_encoder_file = os.path.join(temp_dir, "label_encoder.pkl")
                metadata_file = os.path.join(temp_dir, "metadata.json")
                
                if not os.path.exists(model_file):
                    raise MigrationError("Model file (svm_model.pkl) not found in export")
                
                if not os.path.exists(label_encoder_file):
                    raise MigrationError("Label encoder file (label_encoder.pkl) not found in export")
                
                # Load and validate metadata
                metadata = {}
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    print(f"  ✓ Loaded metadata")
                
                # Validate model compatibility (basic check)
                system_version = metadata.get("system_version", "unknown")
                print(f"  Model system version: {system_version}")
                
                # Create backup of existing model if it exists
                existing_model = os.path.join(self.model_dir, "svm_model.pkl")
                if os.path.exists(existing_model):
                    backup_dir = os.path.join(self.model_dir, "backup")
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    timestamp = self._generate_timestamp()
                    backup_model = os.path.join(backup_dir, f"svm_model_backup_{timestamp}.pkl")
                    backup_encoder = os.path.join(backup_dir, f"label_encoder_backup_{timestamp}.pkl")
                    
                    shutil.copy(existing_model, backup_model)
                    existing_encoder = os.path.join(self.model_dir, "label_encoder.pkl")
                    if os.path.exists(existing_encoder):
                        shutil.copy(existing_encoder, backup_encoder)
                    
                    print(f"  ✓ Backed up existing model to: {backup_dir}")
                
                # Copy model files to model directory
                os.makedirs(self.model_dir, exist_ok=True)
                
                shutil.copy(model_file, os.path.join(self.model_dir, "svm_model.pkl"))
                print(f"  ✓ Imported: svm_model.pkl")
                
                shutil.copy(label_encoder_file, os.path.join(self.model_dir, "label_encoder.pkl"))
                print(f"  ✓ Imported: label_encoder.pkl")
                
                # Copy metadata if exists
                if os.path.exists(metadata_file):
                    shutil.copy(metadata_file, os.path.join(self.model_dir, "model_metadata.json"))
                    print(f"  ✓ Imported: model_metadata.json")
                
                # Display import summary
                print(f"\n  ✓ Model imported successfully!")
                
                if metadata:
                    print(f"\n  Model Details:")
                    if "version_number" in metadata:
                        print(f"    - Version: v{metadata['version_number']}")
                    if "cv_accuracy" in metadata:
                        print(f"    - Accuracy: {metadata['cv_accuracy']:.2%}")
                    if "num_classes" in metadata:
                        print(f"    - Classes: {metadata['num_classes']}")
                    if "classes" in metadata:
                        print(f"    - People: {', '.join(metadata['classes'][:5])}")
                        if len(metadata['classes']) > 5:
                            print(f"      ... and {len(metadata['classes']) - 5} more")
                
                return {
                    "success": True,
                    "metadata": metadata,
                    "model_dir": self.model_dir
                }
            
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        
        except Exception as e:
            raise MigrationError(f"Model import failed: {str(e)}")

    def import_database(self, database_export_path: str, database_url: str, auto_confirm: bool = False) -> Dict[str, Any]:
        """
        Import database training data from SQL dump file.
        
        Args:
            database_export_path: Path to database export SQL file
            database_url: PostgreSQL connection string
            auto_confirm: If True, skip confirmation prompt
            
        Returns:
            Dictionary with import results
            
        Raises:
            MigrationError: If import fails
        """
        print("\n[Import Database] Importing database training data...")
        
        try:
            from urllib.parse import urlparse
            
            # Validate SQL file exists
            if not os.path.exists(database_export_path):
                raise MigrationError(f"Database export file not found: {database_export_path}")
            
            # Parse database URL
            parsed = urlparse(database_url)
            db_host = parsed.hostname or "localhost"
            db_port = parsed.port or 5432
            db_name = (parsed.path or "/face_recognition").lstrip("/")
            db_user = parsed.username or "admin"
            db_password = parsed.password or "admin"
            
            # Analyze SQL file to count records
            print(f"  Analyzing SQL dump...")
            people_count = 0
            faces_count = 0
            
            with open(database_export_path, 'r') as f:
                content = f.read()
                # Count INSERT statements (rough estimate)
                people_count = content.count("INSERT INTO people") + content.count("INSERT INTO public.people")
                faces_count = content.count("INSERT INTO faces") + content.count("INSERT INTO public.faces")
            
            print(f"  Estimated records to import:")
            print(f"    - People: ~{people_count}")
            print(f"    - Faces: ~{faces_count}")
            
            # Prompt for confirmation
            if not auto_confirm:
                print(f"\n  ⚠ WARNING: This will insert data into database: {db_name}@{db_host}")
                print(f"  Existing data will NOT be deleted, but duplicates may cause errors.")
                response = input(f"\n  Continue with import? (yes/no): ").strip().lower()
                
                if response not in ('yes', 'y'):
                    print("  Import cancelled by user")
                    return {"success": False, "cancelled": True}
            
            # Set password environment variable for psql
            env = os.environ.copy()
            env['PGPASSWORD'] = db_password
            
            # Build psql command
            psql_cmd = [
                'psql',
                '-h', db_host,
                '-p', str(db_port),
                '-U', db_user,
                '-d', db_name,
                '-f', database_export_path
            ]
            
            print(f"\n  Importing to database: {db_name}@{db_host}:{db_port}")
            
            # Execute psql
            result = subprocess.run(
                psql_cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Check if error is due to duplicates (which might be acceptable)
                if "duplicate key" in result.stderr.lower():
                    print(f"  ⚠ Warning: Some duplicate records were skipped")
                    print(f"  This is normal if data already exists in the database")
                else:
                    raise MigrationError(f"psql import failed: {result.stderr}")
            
            # Verify import by counting records
            print(f"\n  Verifying import...")
            
            try:
                import psycopg2
                
                conn = psycopg2.connect(
                    host=db_host,
                    port=db_port,
                    database=db_name,
                    user=db_user,
                    password=db_password
                )
                
                cursor = conn.cursor()
                
                # Count people
                cursor.execute("SELECT COUNT(*) FROM people")
                actual_people = cursor.fetchone()[0]
                
                # Count faces
                cursor.execute("SELECT COUNT(*) FROM faces")
                actual_faces = cursor.fetchone()[0]
                
                cursor.close()
                conn.close()
                
                print(f"  ✓ Database verification:")
                print(f"    - People in database: {actual_people}")
                print(f"    - Faces in database: {actual_faces}")
            
            except Exception as e:
                print(f"  ⚠ Warning: Could not verify import: {e}")
            
            print(f"\n  ✓ Database import completed successfully!")
            
            return {
                "success": True,
                "people_count": people_count,
                "faces_count": faces_count
            }
        
        except subprocess.CalledProcessError as e:
            raise MigrationError(f"Database import failed: {str(e)}")
        except Exception as e:
            raise MigrationError(f"Database import failed: {str(e)}")
