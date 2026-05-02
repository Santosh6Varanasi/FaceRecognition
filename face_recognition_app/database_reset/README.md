# Database Reset & System Cleanup Tool

Complete system reset tool that deletes all data and recreates the database from scratch.

## ⚠️ WARNING

**This tool will DELETE EVERYTHING:**
- ❌ All database tables and data
- ❌ All uploaded videos
- ❌ All annotated videos
- ❌ All unknown face images
- ❌ All training images
- ❌ All trained models
- ❌ All person records
- ❌ All detection history

**This action CANNOT be undone!**

## When to Use

Use this tool when you want to:
- Start completely fresh
- Clear all test data
- Reset after major changes
- Clean up before production deployment
- Remove all personal data

## What It Does

### 1. Database Reset
- Drops all existing tables
- Recreates all tables with correct schema
- Creates all indexes
- Resets all sequences
- Clears all data

### 2. File Cleanup
Deletes all files in:
- `video_uploads/` - Uploaded videos
- `video_uploads/annotated/` - Annotated videos
- `unknown_face_images/` - Unknown face images
- `training_images/` - Training images
- `face_recognition_app/flask_api/video_uploads/` - Flask API uploads

## How to Use

### Option 1: Windows Batch File (Easiest)

```bash
cd face_recognition_app/database_reset
.\cleanup.bat
```

### Option 2: Python Script

```bash
cd face_recognition_app/database_reset
python cleanup_all.py
```

## Confirmation Required

The script will ask you to type `DELETE EVERYTHING` to confirm:

```
================================================================================
  COMPLETE SYSTEM CLEANUP
================================================================================

WARNING: This will DELETE ALL DATA including:
  - All database tables and data
  - All uploaded videos
  - All annotated videos
  - All unknown face images
  - All training images
  - All model versions

This action CANNOT be undone!
================================================================================

Type 'DELETE EVERYTHING' to confirm: 
```

## Output Example

```
[Step 1] Connecting to database...
  OK Database connected

[Step 2] Resetting database...
  - Dropping all tables...
  - Recreating all tables...
  - Creating indexes...
  OK Database reset complete
  OK Created 11 tables

[Step 3] Cleaning up files...
  - Video uploads: Deleted 15 files
  - Unknown face images: Deleted 42 files
  - Training images: Deleted 0 files
  - Flask API video uploads: Deleted 8 files
  - Annotated videos: Deleted 8 files
  OK Cleanup complete: 73 files, 0 directories

================================================================================
  CLEANUP SUMMARY
================================================================================

OK System reset complete!

  Database:
    - All tables dropped and recreated
    - All data deleted

  Files:
    - Deleted 73 files
    - Deleted 0 directories

================================================================================

Next steps:
  1. Train a new model:
     cd face_recognition_app/bulk_training_tool
     python bulk_train.py --training-data-dir ../../training_data/training_data

  2. Start Flask API:
     cd face_recognition_app/flask_api
     .\start_app.bat

  3. Start Angular UI:
     cd face_recognition_app/angular_frontend
     npm start

================================================================================
```

## After Cleanup

The system will be in a fresh state:
- ✅ Empty database with all tables
- ✅ No videos or images
- ✅ No trained models
- ✅ No person records
- ✅ Ready for fresh training

### Recommended Next Steps

1. **Train a new model:**
   ```bash
   cd face_recognition_app/bulk_training_tool
   python bulk_train.py --training-data-dir ../../training_data/training_data
   ```

2. **Start Flask API:**
   ```bash
   cd face_recognition_app/flask_api
   .\start_app.bat
   ```

3. **Start Angular UI:**
   ```bash
   cd face_recognition_app/angular_frontend
   npm start
   ```

4. **Test with webcam:**
   ```bash
   cd python_realtime_face_recognition
   python main.py
   ```

## Files in This Folder

```
database_reset/
├── cleanup_all.py      # Main Python cleanup script
├── cleanup.bat         # Windows batch file
├── reset_all.sql       # SQL script to recreate all tables
└── README.md           # This file
```

## Technical Details

### Database Tables Recreated

1. `people` - Person identities
2. `model_versions` - Trained models
3. `faces` - Training face embeddings
4. `unknown_faces` - Unidentified faces
5. `video_sessions` - Camera sessions
6. `frames` - Video frames
7. `detections` - Face detections
8. `videos` - Uploaded videos
9. `video_jobs` - Processing jobs
10. `video_detections` - Video face detections
11. `timeline_entries` - Person appearance timelines

### Indexes Created

All necessary indexes are recreated for optimal performance:
- Primary keys
- Foreign keys
- Search indexes
- Timestamp indexes

### Extensions

- `vector` extension for pgvector (face embeddings)

## Safety Features

1. **Confirmation Required** - Must type exact phrase
2. **Clear Warnings** - Multiple warnings before execution
3. **Detailed Logging** - Shows exactly what's being deleted
4. **Error Handling** - Graceful failure with error messages
5. **Summary Report** - Shows what was deleted

## Troubleshooting

### "Database connection failed"
**Solution:** Ensure PostgreSQL is running and `.env` is configured

### "Permission denied"
**Solution:** Run as administrator or check file permissions

### "SQL script not found"
**Solution:** Ensure you're running from `database_reset/` directory

### "Some files couldn't be deleted"
**Solution:** Close any applications using those files (Flask API, video players, etc.)

## Important Notes

- ⚠️ **Stop Flask API** before running cleanup
- ⚠️ **Close all video players** before running cleanup
- ⚠️ **Backup important data** before running cleanup
- ⚠️ **Cannot be undone** - all data will be permanently deleted

## Alternative: Manual Cleanup

If you prefer manual cleanup:

### 1. Database Only
```sql
-- Run in PostgreSQL
\i face_recognition_app/database_reset/reset_all.sql
```

### 2. Files Only
```bash
# Windows
rmdir /s /q video_uploads
rmdir /s /q unknown_face_images
rmdir /s /q training_images

# Linux/Mac
rm -rf video_uploads/*
rm -rf unknown_face_images/*
rm -rf training_images/*
```

## Support

If you encounter issues:
1. Check PostgreSQL is running
2. Check `.env` configuration
3. Ensure no applications are using the files
4. Run as administrator if permission errors
5. Check logs for detailed error messages
