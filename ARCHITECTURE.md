# System Architecture

## 📐 Overview

The Face Recognition Application follows a three-tier architecture with clear separation of concerns:

1. **Presentation Layer**: Angular frontend
2. **Application Layer**: Flask REST API
3. **Data Layer**: PostgreSQL database

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                            │
│                     (Angular Application)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST API
                             │ (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FLASK API SERVER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Routes Layer                       │  │
│  │  /api/videos  /api/faces  /api/model  /api/unknown-faces│  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                   Service Layer                           │  │
│  │  VideoProcessor  FaceRecognition  ModelRetrainer         │  │
│  │  BulkOperations  InferenceService                        │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                   Data Access Layer                       │  │
│  │  Database Queries  Connection Pool  Transactions         │  │
│  └────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            │ SQL
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Videos  │  │  People  │  │  Faces   │  │  Models  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 🎨 Frontend Architecture (Angular)

### Component Hierarchy

```
AppComponent
├── DashboardComponent
│   ├── KpiCardComponent
│   └── StatisticsComponent
├── VideoComponent
│   └── VideoListComponent
├── VideoPlaybackComponent
│   ├── VideoPlayerComponent
│   ├── DetectionOverlayComponent
│   └── TimelineComponent
├── UnknownFacesComponent
│   ├── FaceCardComponent
│   └── ConfirmationDialogComponent
├── PeopleComponent
│   └── PeopleListComponent
├── ModelManagementComponent
│   └── RetrainingProgressComponent
└── CameraMonitorComponent
```

### Service Layer

```typescript
// Core Services
- VideoService: Video operations (upload, process, retrieve)
- FaceApiService: Face management (label, delete, bulk operations)
- InferenceService: Real-time face recognition
- ModelService: Model training and management

// Utility Services
- RetrainingPollerService: Poll retraining job status
- WebSocketService: Real-time updates (future)
- AuthService: Authentication (future)
```

### State Management

- **RxJS BehaviorSubjects**: For reactive state management
- **Observables**: For async data streams
- **Local Component State**: For UI-specific state

### Routing

```typescript
const routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'video', component: VideoComponent },
  { path: 'video/:id/playback', component: VideoPlaybackComponent },
  { path: 'unknown-faces', component: UnknownFacesComponent },
  { path: 'people', component: PeopleComponent },
  { path: 'model', component: ModelManagementComponent },
  { path: 'camera', component: CameraMonitorComponent }
];
```

## 🔧 Backend Architecture (Flask)

### Directory Structure

```
flask_api/
├── app.py                      # Application entry point
├── config.py                   # Configuration management
├── db/
│   ├── connection.py           # Database connection pool
│   └── queries.py              # SQL query functions
├── routes/
│   ├── video.py                # Video endpoints
│   ├── unknown_faces.py        # Unknown face endpoints
│   ├── model.py                # Model management endpoints
│   ├── people.py               # People endpoints
│   └── health.py               # Health check endpoint
├── services/
│   ├── video_processor.py      # Video processing logic
│   ├── inference_service.py    # Face recognition inference
│   ├── model_retrainer.py      # Model training logic
│   ├── bulk_operations.py      # Bulk operations handler
│   └── face_detection.py       # Face detection service
├── models/
│   ├── face_recognition_model.pkl
│   ├── label_encoder.pkl
│   └── model_metadata.pkl
└── tests/
    ├── test_video_processor.py
    ├── test_bulk_operations.py
    └── test_model_retrainer.py
```

### Service Layer Design

#### VideoProcessorService

```python
class VideoProcessorService:
    def upload_video(file, metadata) -> VideoRecord
    def process_video(video_id) -> ProcessingResult
    def get_detections_at_timestamp(video_id, timestamp, tolerance) -> List[Detection]
    def get_timeline(video_id) -> List[TimelineEntry]
    def reprocess_video(video_id, model_version) -> ProcessingResult
```

#### InferenceService

```python
class InferenceService:
    def detect_faces(image) -> List[FaceLocation]
    def recognize_face(face_encoding) -> RecognitionResult
    def extract_embedding(face_image) -> np.ndarray
    def calculate_similarity(embedding1, embedding2) -> float
```

#### ModelRetrainerService

```python
class ModelRetrainerService:
    def trigger_retrain() -> str  # Returns job_id
    def train_model() -> ModelMetadata
    def get_retrain_status(job_id) -> JobStatus
    def save_model(model, metadata) -> int  # Returns version_number
```

#### BulkOperationHandler

```python
class BulkOperationHandler:
    def get_affected_count(filter_status) -> int
    def bulk_delete(filter_status) -> BulkOperationResult
    def bulk_reject(filter_status) -> BulkOperationResult
```

### API Design Patterns

#### RESTful Endpoints

```
GET    /api/videos              # List videos
POST   /api/videos/upload       # Upload video
GET    /api/videos/{id}         # Get video details
POST   /api/videos/{id}/process # Process video
GET    /api/videos/{id}/detections?timestamp=10.5
GET    /api/videos/{id}/timeline

GET    /api/unknown-faces       # List unknown faces
POST   /api/unknown-faces/{id}/label
POST   /api/unknown-faces/bulk-delete
POST   /api/unknown-faces/bulk-reject
GET    /api/unknown-faces/count

POST   /api/model/retrain       # Trigger retraining
GET    /api/model/retrain/status/{job_id}
GET    /api/model/versions      # List model versions
```

#### Response Format

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2026-04-29T10:30:00Z"
}
```

#### Error Format

```json
{
  "success": false,
  "error": {
    "code": "VIDEO_NOT_FOUND",
    "message": "Video with ID 123 not found",
    "details": { ... }
  },
  "timestamp": "2026-04-29T10:30:00Z"
}
```

## 🗄️ Database Architecture

### Entity Relationship Diagram

```
┌─────────────┐         ┌─────────────┐
│   People    │◄────────┤ Labeled     │
│             │         │   Faces     │
│ id (PK)     │         │             │
│ name        │         │ id (PK)     │
│ created_at  │         │ person_id   │
└──────┬──────┘         │ image_path  │
       │                │ embedding   │
       │                └─────────────┘
       │
       │                ┌─────────────┐
       │                │  Unknown    │
       │                │   Faces     │
       │                │             │
       │                │ id (PK)     │
       │                │ image_path  │
       │                │ embedding   │
       │                │ status      │
       │                │ source_video│
       │                └─────────────┘
       │
       │                ┌─────────────┐
       └────────────────┤   Video     │
                        │ Detections  │
                        │             │
                        │ id (PK)     │
                        │ video_id    │
                        │ person_id   │
                        │ timestamp   │
                        │ bbox_*      │
                        │ confidence  │
                        └──────┬──────┘
                               │
                               │
                        ┌──────▼──────┐
                        │   Videos    │
                        │             │
                        │ id (PK)     │
                        │ filename    │
                        │ duration    │
                        │ status      │
                        │ model_ver   │
                        └──────┬──────┘
                               │
                               │
                        ┌──────▼──────┐
                        │  Timeline   │
                        │   Entries   │
                        │             │
                        │ id (PK)     │
                        │ video_id    │
                        │ person_id   │
                        │ start_time  │
                        │ end_time    │
                        └─────────────┘
```

### Table Descriptions

#### people
- Stores unique person identities
- Referenced by labeled_faces and video_detections

#### labeled_faces
- Training data for face recognition model
- Contains face embeddings (128-dimensional vectors)
- Links to person identity

#### unknown_faces
- Faces detected but not recognized
- Can be labeled to become training data
- Supports bulk operations (delete, reject)
- Tracks source video for context

#### videos
- Metadata for uploaded videos
- Tracks processing status
- Records model version used

#### video_detections
- Frame-by-frame detection results
- Stores bounding box coordinates
- Links to person identity (if recognized)
- Includes confidence scores

#### timeline_entries
- Aggregated view of person appearances
- Groups consecutive detections
- Optimized for timeline visualization

#### model_versions
- Tracks trained model versions
- Stores training metrics
- Supports model rollback

#### retraining_jobs
- Manages async retraining jobs
- Tracks progress and status
- Stores training results

### Indexing Strategy

```sql
-- High-frequency queries
CREATE INDEX idx_video_detections_video_timestamp ON video_detections(video_id, timestamp);
CREATE INDEX idx_unknown_faces_status ON unknown_faces(status);
CREATE INDEX idx_videos_status ON videos(status);

-- Foreign key optimization
CREATE INDEX idx_labeled_faces_person_id ON labeled_faces(person_id);
CREATE INDEX idx_video_detections_person_id ON video_detections(person_id);

-- Sorting optimization
CREATE INDEX idx_unknown_faces_created_at ON unknown_faces(created_at DESC);
CREATE INDEX idx_videos_uploaded_at ON videos(uploaded_at DESC);
```

## 🤖 Machine Learning Pipeline

### Face Recognition Flow

```
Input Image/Video Frame
        │
        ▼
┌───────────────────┐
│  Face Detection   │  (dlib HOG/CNN)
│  (face_recognition)│
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Face Alignment    │  (68 facial landmarks)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Face Encoding     │  (128-d embedding)
│  (ResNet model)   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ SVM Classification│  (RBF kernel)
│  (scikit-learn)   │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Person Identity   │  + Confidence Score
│  + Confidence     │
└───────────────────┘
```

### Model Training Pipeline

```
Training Data (training_data/)
        │
        ▼
┌───────────────────┐
│ Load Images       │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Extract Embeddings│  (face_recognition)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Label Encoding    │  (LabelEncoder)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Train SVM         │  (5-fold CV)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Save Model        │  (.pkl files)
└───────────────────┘
```

## 🔄 Data Flow

### Video Processing Flow

```
1. User uploads video
   ↓
2. VideoProcessorService.upload_video()
   - Validate format
   - Extract metadata (OpenCV)
   - Calculate file hash
   - Store to filesystem
   - Save metadata to database
   ↓
3. User triggers processing
   ↓
4. VideoProcessorService.process_video()
   - Extract frames (1 FPS)
   - For each frame:
     * Detect faces
     * Recognize faces
     * Store detections
     * Extract unknown faces
   - Generate timeline entries
   ↓
5. Results available for playback
```

### Face Labeling Flow

```
1. User views unknown faces
   ↓
2. User labels face with person name
   ↓
3. FaceApiService.label_face()
   - Check if person exists
   - Create person if new
   - Move face to labeled_faces
   - Update status
   ↓
4. Face becomes training data
   ↓
5. User triggers model retraining
   ↓
6. ModelRetrainerService.train_model()
   - Load all labeled faces
   - Train new SVM model
   - Save model with version
   ↓
7. New model available for recognition
```

## 🔐 Security Architecture

### Authentication (Future)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Login (username/password)
       ▼
┌─────────────┐
│  Auth API   │
└──────┬──────┘
       │ 2. Validate credentials
       ▼
┌─────────────┐
│  Database   │
└──────┬──────┘
       │ 3. Return user data
       ▼
┌─────────────┐
│  Auth API   │
└──────┬──────┘
       │ 4. Generate JWT token
       ▼
┌─────────────┐
│   Client    │  (Store token)
└──────┬──────┘
       │ 5. Subsequent requests with token
       ▼
┌─────────────┐
│  API Routes │  (Verify token)
└─────────────┘
```

### Data Protection

- **Passwords**: Bcrypt hashing (future)
- **API Keys**: Environment variables
- **Database**: SSL connections
- **File Uploads**: Virus scanning (future)
- **Face Embeddings**: Encrypted at rest (future)

## 📊 Performance Considerations

### Caching Strategy

```
┌─────────────────────────────────────┐
│         Application Cache            │
├─────────────────────────────────────┤
│ - Model in memory (singleton)       │
│ - Label encoder in memory           │
│ - Recent video metadata (LRU)       │
│ - Detection results (5 min TTL)     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         Database Cache               │
├─────────────────────────────────────┤
│ - Query result cache                │
│ - Connection pooling                │
│ - Prepared statements               │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         CDN/Nginx Cache              │
├─────────────────────────────────────┤
│ - Static assets (images, videos)    │
│ - API responses (short TTL)         │
└─────────────────────────────────────┘
```

### Async Processing

- **Video Processing**: Background threads
- **Model Training**: Async jobs with status polling
- **Bulk Operations**: Transaction batching

### Database Optimization

- **Indexes**: On frequently queried columns
- **Partitioning**: Videos by date (future)
- **Archiving**: Old detections (future)
- **Connection Pooling**: Reuse connections

## 🔮 Future Enhancements

### Planned Features

1. **Real-time Processing**: WebSocket for live camera feeds
2. **Distributed Processing**: Celery for task queue
3. **Microservices**: Split into smaller services
4. **GraphQL API**: Alternative to REST
5. **Mobile App**: React Native frontend
6. **Cloud Storage**: S3 for videos and images
7. **Advanced Analytics**: Face clustering, demographics
8. **Multi-tenancy**: Support multiple organizations

### Scalability Roadmap

```
Current: Monolithic
    ↓
Phase 1: Horizontal scaling (load balancer)
    ↓
Phase 2: Service separation (video, face, model)
    ↓
Phase 3: Microservices architecture
    ↓
Phase 4: Kubernetes orchestration
```

## 📚 Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Angular 17 | UI framework |
| Frontend | TypeScript | Type-safe JavaScript |
| Frontend | RxJS | Reactive programming |
| Frontend | HTML5 Canvas | Detection overlay |
| Backend | Flask 2.x | Web framework |
| Backend | Python 3.8+ | Programming language |
| Backend | Gunicorn | WSGI server |
| ML | face_recognition | Face detection/encoding |
| ML | dlib | Face detection |
| ML | scikit-learn | SVM classifier |
| ML | OpenCV | Video processing |
| Database | PostgreSQL 12+ | Relational database |
| Deployment | Nginx | Reverse proxy |
| Deployment | Docker | Containerization |
| Deployment | systemd | Service management |
