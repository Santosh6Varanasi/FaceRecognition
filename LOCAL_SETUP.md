# Local Development Setup Guide

Complete step-by-step guide to set up the Face Recognition Application on your local machine.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] Node.js 16.x or higher installed
- [ ] PostgreSQL 12.x or higher installed
- [ ] Git installed
- [ ] 8GB RAM minimum (16GB recommended)
- [ ] 10GB free disk space
- [ ] Administrator/sudo access

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone repository
git clone <repository-url>
cd FaceRecornization

# 2. Setup database
psql -U postgres -c "CREATE DATABASE face_recognition;"
psql -U postgres -d face_recognition -f face_recognition_app/database/CREATE_ALL_FRESH.sql

# 3. Setup backend
cd face_recognition_app/flask_api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Train model
cd ../..
python train_model_standalone.py

# 5. Start backend
cd face_recognition_app/flask_api
python app.py

# 6. Setup frontend (new terminal)
cd face_recognition_app/angular_frontend
npm install
npm start

# 7. Open browser
# Navigate to http://localhost:4200
```

## 📝 Detailed Setup Instructions

### Step 1: Install Python

#### Windows

1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:

```cmd
python --version
pip --version
```

#### macOS

```bash
# Using Homebrew
brew install python@3.9

# Verify
python3 --version
pip3 --version
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Verify
python3 --version
pip3 --version
```

### Step 2: Install Node.js

#### Windows

1. Download from [nodejs.org](https://nodejs.org/)
2. Run installer
3. Accept defaults
4. Verify:

```cmd
node --version
npm --version
```

#### macOS

```bash
# Using Homebrew
brew install node@16

# Verify
node --version
npm --version
```

#### Linux (Ubuntu/Debian)

```bash
# Using NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version
npm --version
```

### Step 3: Install PostgreSQL

#### Windows

1. Download from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run installer
3. Remember the password you set for `postgres` user
4. Default port: 5432
5. Verify:

```cmd
psql --version
```

#### macOS

```bash
# Using Homebrew
brew install postgresql@13
brew services start postgresql@13

# Verify
psql --version
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify
psql --version
```

### Step 4: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd FaceRecornization

# Verify you're in the right directory
ls -la
# You should see: face_recognition_app/, training_data/, etc.
```

### Step 5: Database Setup

#### Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt:
CREATE DATABASE face_recognition;
\q
```

#### Run Schema Creation

```bash
# From project root
cd face_recognition_app/database

# Run creation script
psql -U postgres -d face_recognition -f CREATE_ALL_FRESH.sql

# Verify tables were created
psql -U postgres -d face_recognition -c "\dt"
```

You should see 8 tables:
- people
- labeled_faces
- unknown_faces
- videos
- video_detections
- timeline_entries
- model_versions
- retraining_jobs

### Step 6: Backend Setup

#### Create Virtual Environment

```bash
# Navigate to Flask API directory
cd face_recognition_app/flask_api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Your prompt should now show (venv)
```

#### Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# This will install:
# - Flask
# - face_recognition
# - opencv-python
# - scikit-learn
# - psycopg2
# - and other dependencies
```

**Note:** Installation may take 5-10 minutes depending on your internet speed.

#### Configure Environment

Create `.env` file in `face_recognition_app/flask_api/`:

```bash
# Create .env file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=face_recognition
DB_USER=postgres
DB_PASSWORD=your_postgres_password
FLASK_ENV=development
SECRET_KEY=dev_secret_key_change_in_production
EOF
```

**Important:** Replace `your_postgres_password` with your actual PostgreSQL password.

#### Verify Backend Setup

```bash
# Test database connection
python -c "import psycopg2; print('Database connection: OK')"

# Test face_recognition library
python -c "import face_recognition; print('face_recognition: OK')"

# Test OpenCV
python -c "import cv2; print('OpenCV: OK')"
```

### Step 7: Prepare Training Data

#### Create Training Data Directory

```bash
# From project root
mkdir -p training_data

# Create subdirectories for each person
mkdir -p training_data/person1
mkdir -p training_data/person2
mkdir -p training_data/person3
```

#### Add Training Photos

```
training_data/
├── person1/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
├── person2/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.jpg
└── person3/
    ├── photo1.jpg
    └── photo2.jpg
```

**Requirements:**
- Use clear, front-facing photos
- One face per image
- Good lighting
- 3-10 photos per person
- Supported formats: JPG, JPEG, PNG

### Step 8: Train Model

```bash
# From project root
python train_model_standalone.py
```

**Expected Output:**
```
================================================================================
  FACE RECOGNITION MODEL TRAINING
================================================================================
Training data directory: training_data
Model output directory: face_recognition_app/models

[Step 1] Validating training data directory
✓ Found 3 person directories
  - person1: 3 images
  - person2: 3 images
  - person3: 2 images
✓ Total training images: 8

[Step 2] Loading and encoding training images
  Processing person1...
    ✓ photo1.jpg
    ✓ photo2.jpg
    ✓ photo3.jpg
  Processing person2...
    ✓ photo1.jpg
    ✓ photo2.jpg
    ✓ photo3.jpg
  Processing person3...
    ✓ photo1.jpg
    ✓ photo2.jpg
✓ Successfully encoded 8 faces

[Step 3] Training SVM classifier
  - Number of classes: 3
  - Number of training samples: 8
  - Classes: person1, person2, person3
  Training SVM (kernel=rbf, C=1.0)...
✓ Model trained successfully
  Performing 5-fold cross-validation...
✓ Cross-validation accuracy: 85.00% (+/- 10.00%)

[Step 4] Saving model
✓ Model saved to face_recognition_app/models/face_recognition_model.pkl
✓ Label encoder saved to face_recognition_app/models/label_encoder.pkl
✓ Metadata saved to face_recognition_app/models/model_metadata.pkl

✓ Training completed successfully!
```

### Step 9: Start Backend Server

```bash
# Navigate to Flask API directory
cd face_recognition_app/flask_api

# Activate virtual environment (if not already activated)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start Flask server
python app.py
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

**Verify Backend:**
Open browser and navigate to: `http://localhost:5000/api/health`

You should see:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-29T10:30:00Z"
}
```

### Step 10: Frontend Setup

#### Open New Terminal

Keep the backend running and open a new terminal.

#### Install Dependencies

```bash
# Navigate to Angular frontend directory
cd face_recognition_app/angular_frontend

# Install dependencies
npm install

# This will install Angular and all dependencies
# May take 5-10 minutes
```

#### Start Development Server

```bash
# Start Angular dev server
npm start
```

**Expected Output:**
```
✔ Browser application bundle generation complete.
Initial Chunk Files | Names         |  Raw Size
polyfills.js        | polyfills     |  90.20 kB | 
main.js             | main          |  50.00 kB | 
styles.css          | styles        |  10.00 kB | 

                    | Initial Total | 150.20 kB

Application bundle generation complete. [5.123 seconds]
Watch mode enabled. Watching for file changes...
  ➜  Local:   http://localhost:4200/
```

### Step 11: Access Application

1. Open your browser
2. Navigate to: `http://localhost:4200`
3. You should see the Face Recognition Application dashboard

## ✅ Verification Checklist

Test each feature to ensure everything works:

- [ ] Dashboard loads successfully
- [ ] Can navigate to different pages
- [ ] Can upload an image for face recognition
- [ ] Can view unknown faces
- [ ] Can label unknown faces
- [ ] Can view people list
- [ ] Can trigger model retraining
- [ ] Can upload a video
- [ ] Can process a video
- [ ] Can view video playback with detection overlay

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'face_recognition'"

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Reinstall face_recognition
pip install face_recognition
```

### Issue: "psycopg2.OperationalError: could not connect to server"

**Solution:**
```bash
# Check if PostgreSQL is running
# On Windows:
services.msc  # Look for PostgreSQL service

# On macOS:
brew services list

# On Linux:
sudo systemctl status postgresql

# Start PostgreSQL if not running
# On macOS:
brew services start postgresql@13

# On Linux:
sudo systemctl start postgresql
```

### Issue: "Database 'face_recognition' does not exist"

**Solution:**
```bash
# Create database
psql -U postgres -c "CREATE DATABASE face_recognition;"

# Run schema
psql -U postgres -d face_recognition -f face_recognition_app/database/CREATE_ALL_FRESH.sql
```

### Issue: "Port 5000 already in use"

**Solution:**
```bash
# Find process using port 5000
# On Windows:
netstat -ano | findstr :5000

# On macOS/Linux:
lsof -i :5000

# Kill the process or change Flask port
# In app.py, change:
app.run(debug=True, port=5001)
```

### Issue: "Port 4200 already in use"

**Solution:**
```bash
# Change Angular port
ng serve --port 4201
```

### Issue: "No face detected in training images"

**Solution:**
- Ensure images have clear, front-facing faces
- Check image quality and lighting
- Try different photos
- Verify image format (JPG, JPEG, PNG)

### Issue: "Low model accuracy (<70%)"

**Solution:**
- Add more training photos per person (aim for 5-10)
- Use diverse photos (different angles, lighting)
- Remove poor quality images
- Ensure faces are clearly visible

### Issue: "npm install fails"

**Solution:**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

## 🔄 Daily Development Workflow

### Starting Work

```bash
# Terminal 1: Backend
cd face_recognition_app/flask_api
source venv/bin/activate  # On Windows: venv\Scripts\activate
python app.py

# Terminal 2: Frontend
cd face_recognition_app/angular_frontend
npm start
```

### Stopping Work

```bash
# Press Ctrl+C in both terminals
# Deactivate virtual environment
deactivate
```

### Updating Code

```bash
# Pull latest changes
git pull

# Update backend dependencies
cd face_recognition_app/flask_api
source venv/bin/activate
pip install -r requirements.txt

# Update frontend dependencies
cd face_recognition_app/angular_frontend
npm install
```

### Database Reset

```bash
# Clean database
psql -U postgres -d face_recognition -f face_recognition_app/database/CLEANUP_ALL.sql

# Recreate schema
psql -U postgres -d face_recognition -f face_recognition_app/database/CREATE_ALL_FRESH.sql

# Retrain model
python train_model_standalone.py
```

## 📚 Additional Resources

### Documentation
- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [DATABASE.md](DATABASE.md) - Database documentation
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment

### External Resources
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Angular Documentation](https://angular.io/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [face_recognition Library](https://github.com/ageitgey/face_recognition)

## 🆘 Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Review error messages in terminal
3. Check browser console for frontend errors
4. Review Flask logs for backend errors
5. Verify all prerequisites are installed
6. Ensure database is running and accessible

## 🎉 Success!

If you've completed all steps, you should have:

✅ PostgreSQL database running
✅ Backend Flask API running on port 5000
✅ Frontend Angular app running on port 4200
✅ Face recognition model trained
✅ Application accessible in browser

You're ready to start developing!
