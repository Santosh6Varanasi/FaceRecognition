# Face Recognition Application

A comprehensive face recognition system with video processing capabilities, built with Flask (backend) and Angular (frontend).

## 🎯 Features

### Core Features
- **Real-time Face Recognition**: Detect and recognize faces in images and videos
- **Video Processing**: Upload and process videos with frame-by-frame face detection
- **Unknown Face Management**: Identify, label, and manage unknown faces
- **Model Training**: Train custom face recognition models with your own data
- **Interactive Timeline**: Visual timeline showing when people appear in videos
- **Bulk Operations**: Efficiently manage multiple unknown faces at once

### Advanced Features
- **Detection Overlay**: Real-time bounding boxes and labels on video playback
- **Model Retraining**: Retrain models with new labeled faces
- **Video Reprocessing**: Reprocess videos with updated models
- **Face Deduplication**: Automatic detection of duplicate faces
- **Confidence Scoring**: Recognition confidence levels for each detection

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Database Setup](#database-setup)
- [Model Training](#model-training)
- [Running the Application](#running-the-application)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)

## 💻 System Requirements

### Software Requirements
- **Python**: 3.8 or higher
- **Node.js**: 16.x or higher
- **PostgreSQL**: 12.x or higher
- **npm**: 8.x or higher

### Hardware Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: 10GB free space
- **CPU**: Multi-core processor recommended for video processing

### Operating Systems
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+, Debian 10+)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd FaceRecornization
```

### 2. Backend Setup (Flask API)

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

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup (Angular)

```bash
# Navigate to Angular frontend directory
cd face_recognition_app/angular_frontend

# Install dependencies
npm install
```

## 🗄️ Database Setup

### 1. Install PostgreSQL

Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/)

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE face_recognition;

# Exit psql
\q
```

### 3. Configure Database Connection

Create `.env` file in `face_recognition_app/flask_api/`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=face_recognition
DB_USER=postgres
DB_PASSWORD=your_password
```

### 4. Initialize Database

```bash
# From project root directory
cd face_recognition_app/database

# Run cleanup script (if needed)
psql -U postgres -d face_recognition -f CLEANUP_ALL.sql

# Run creation script
psql -U postgres -d face_recognition -f CREATE_ALL_FRESH.sql
```

## 🎓 Model Training

### 1. Prepare Training Data

Create a `training_data` directory in the project root with subdirectories for each person:

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
- Each person should have their own subdirectory
- Directory name will be used as the person's name
- Include 3-10 photos per person for best results
- Use clear, front-facing photos
- Supported formats: JPG, JPEG, PNG

### 2. Train the Model

```bash
# From project root directory
python train_model_standalone.py
```

The script will:
- Validate your training data
- Extract face encodings from all images
- Train an SVM classifier
- Perform cross-validation
- Save the model to `face_recognition_app/models/`

### 3. Verify Training

Check the output for:
- Number of classes (people)
- Number of training samples
- Cross-validation accuracy
- Any failed images

**Tip:** Aim for at least 70% cross-validation accuracy. If lower, add more diverse photos for each person.

## 🏃 Running the Application

### 1. Start Backend (Flask API)

```bash
# Navigate to Flask API directory
cd face_recognition_app/flask_api

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Start Flask server
python app.py
```

Backend will run on: `http://localhost:5000`

### 2. Start Frontend (Angular)

```bash
# Open new terminal
# Navigate to Angular frontend directory
cd face_recognition_app/angular_frontend

# Start development server
npm start
```

Frontend will run on: `http://localhost:4200`

### 3. Access the Application

Open your browser and navigate to: `http://localhost:4200`

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Angular Frontend                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Dashboard  │  │ Video Player │  │ Face Manager │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Video Service│  │  Face Service│  │ Model Service│     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Videos    │  │    Faces     │  │    People    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Frontend:**
- Angular 17.x
- TypeScript
- RxJS
- HTML5 Canvas (for detection overlay)

**Backend:**
- Flask 2.x
- Python 3.8+
- face_recognition library
- scikit-learn (SVM classifier)
- OpenCV (video processing)

**Database:**
- PostgreSQL 12+

**ML/AI:**
- dlib (face detection)
- face_recognition (face encoding)
- SVM (classification)

## 📚 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Video Operations

**Upload Video**
```http
POST /videos/upload
Content-Type: multipart/form-data

Body: video file
Response: { id, filename, duration, status }
```

**Process Video**
```http
POST /videos/{video_id}/process
Response: { status: "processing" }
```

**Get Video Metadata**
```http
GET /videos/{video_id}
Response: { id, filename, duration, fps, width, height, status }
```

**Get Detections**
```http
GET /videos/{video_id}/detections?timestamp=10.5&tolerance=0.25
Response: [{ person_name, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2 }]
```

**Get Timeline**
```http
GET /videos/{video_id}/timeline
Response: [{ person_name, start_time, end_time, detection_count }]
```

#### Face Management

**Get Unknown Faces**
```http
GET /unknown-faces?status=pending&page=1&page_size=20
Response: { items: [...], total, page, page_size }
```

**Label Face**
```http
POST /unknown-faces/{face_id}/label
Body: { person_name: "John Doe" }
Response: { success: true }
```

**Bulk Delete**
```http
POST /unknown-faces/bulk-delete
Body: { filter_status: "rejected" }
Response: { success_count, failed_count }
```

**Bulk Reject**
```http
POST /unknown-faces/bulk-reject
Body: { filter_status: "pending" }
Response: { success_count, failed_count }
```

#### Model Management

**Trigger Retraining**
```http
POST /model/retrain
Response: { job_id }
```

**Get Retraining Status**
```http
GET /model/retrain/status/{job_id}
Response: { status, progress_pct, message, cv_accuracy }
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Database Connection Error

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
- Verify PostgreSQL is running
- Check database credentials in `.env` file
- Ensure database exists: `psql -U postgres -l`

#### 2. Model Not Found

**Problem:** `FileNotFoundError: face_recognition_model.pkl not found`

**Solution:**
- Run the training script: `python train_model_standalone.py`
- Ensure `training_data/` directory has person subdirectories with photos

#### 3. Low Model Accuracy

**Problem:** Cross-validation accuracy below 70%

**Solution:**
- Add more photos per person (aim for 5-10)
- Use diverse photos (different angles, lighting)
- Ensure photos are clear and faces are visible
- Remove poor quality images

#### 4. Video Processing Fails

**Problem:** Video upload succeeds but processing fails

**Solution:**
- Check video format (supported: mp4, avi, mov)
- Verify OpenCV is installed: `pip install opencv-python`
- Check Flask logs for detailed error messages

#### 5. Frontend Can't Connect to Backend

**Problem:** `HttpErrorResponse: 0 Unknown Error`

**Solution:**
- Verify Flask server is running on port 5000
- Check CORS configuration in Flask app
- Ensure no firewall blocking localhost connections

#### 6. Numpy Version Error

**Problem:** `ModuleNotFoundError: No module named 'numpy.exceptions'`

**Solution:**
```bash
pip install --upgrade numpy>=1.26.4
```

### Getting Help

If you encounter issues not covered here:

1. Check Flask logs in terminal running `app.py`
2. Check browser console for frontend errors
3. Review database logs: `tail -f /var/log/postgresql/postgresql-12-main.log`
4. Verify all dependencies are installed correctly

## 📝 License

[Add your license information here]

## 👥 Contributors

[Add contributor information here]

## 📧 Contact

[Add contact information here]
