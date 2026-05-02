"""
Video routes — upload, job status, list, and detections.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import hashlib
import threading
import uuid

from flask import Blueprint, jsonify, request

from db import queries
from services.video_processor import process_video
from middleware.logging_middleware import log_request_response

video_bp = Blueprint("video_bp", __name__, url_prefix="/api/videos")

uploads_dir = os.environ.get(
    'VIDEO_UPLOADS_DIR',
    os.path.join(os.path.dirname(__file__), '..', 'video_uploads'),
)
os.makedirs(uploads_dir, exist_ok=True)

_ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}


@video_bp.route("", methods=["GET"])
@video_bp.route("/", methods=["GET"])
@log_request_response
def list_videos_root():
    """
    Return a paginated list of uploaded videos (alternative endpoint).
    Supports query parameters: page, page_size, status
    """
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status', None)  # Optional status filter

    db = queries.get_db_connection()
    videos, total = queries.list_videos(db, page, page_size, status)

    for video in videos:
        for key in ('uploaded_at', 'last_processed_at'):
            if video.get(key) is not None:
                video[key] = video[key].isoformat()

    return jsonify({"videos": videos, "total": total, "page": page, "page_size": page_size}), 200


@video_bp.route("/upload", methods=["POST"])
@log_request_response
def upload_video():
    """Accept a video file, persist it, and start an async processing job."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug logging
    logger.info(f"Upload request received. Content-Type: {request.content_type}")
    logger.info(f"Files in request: {list(request.files.keys())}")
    logger.info(f"Form data: {list(request.form.keys())}")
    
    if 'file' not in request.files:
        logger.error("No 'file' key in request.files")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    
    if not file.filename:
        logger.error("File has no filename")
        return jsonify({"error": "No file selected"}), 400
    
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in _ALLOWED_EXTENSIONS:
        logger.error(f"Unsupported file extension: {ext}")
        return jsonify({"error": "Unsupported file format. Please upload MP4, AVI, MOV, or MKV."}), 400

    file_bytes = file.read()

    max_bytes = int(os.environ.get('VIDEO_MAX_FILE_SIZE_MB', 100)) * 1024 * 1024
    if len(file_bytes) > max_bytes:
        logger.error(f"File size {len(file_bytes)} exceeds limit {max_bytes}")
        return jsonify({"error": f"File size exceeds the {max_bytes // (1024*1024)}MB limit"}), 400

    video_hash = hashlib.sha256(file_bytes).hexdigest()
    filename = file.filename

    db = queries.get_db_connection()
    existing = queries.get_video_by_hash(db, video_hash)

    if existing:
        video_id = existing['id']
        file_path = existing['file_path']
    else:
        file_path = os.path.join(uploads_dir, f'{video_hash}.{ext}')
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        video_id = queries.insert_video(
            db, filename, file_path, len(file_bytes), video_hash,
            None, None, None, None,
        )

    job_id = str(uuid.uuid4())
    queries.insert_video_job(db, job_id, video_id)

    threading.Thread(
        target=process_video,
        args=(video_id, job_id, file_path, db),
        daemon=True,
    ).start()

    return jsonify({"video_id": video_id, "job_id": job_id}), 202


@video_bp.route("/job/<job_id>", methods=["GET"])
@log_request_response
def get_job_status(job_id: str):
    """Return the current status of a video processing job."""
    db = queries.get_db_connection()
    job = queries.get_video_job(db, job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "status": job["status"],
        "progress_pct": job["progress_pct"],
        "frames_processed": job["frames_processed"],
        "total_frames": job["total_frames"],
        "message": job["message"],
        "unique_unknowns": job["unique_unknowns"],
        "unique_known": job["unique_known"],
    }), 200


@video_bp.route("/list", methods=["GET"])
@log_request_response
def list_videos():
    """Return a paginated list of uploaded videos."""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    status = request.args.get('status', None)  # Optional status filter

    db = queries.get_db_connection()
    videos, total = queries.list_videos(db, page, page_size, status)

    for video in videos:
        for key in ('uploaded_at', 'last_processed_at'):
            if video.get(key) is not None:
                video[key] = video[key].isoformat()

    return jsonify({"videos": videos, "total": total, "page": page, "page_size": page_size}), 200


@video_bp.route("/<int:video_id>/frames", methods=["GET"])
@log_request_response
def get_video_frames(video_id: int):
    """Return frame-by-frame breakdown for a processed video."""
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    # Check if video has been processed
    if video.get("status") != "processed":
        return jsonify({"error": "Video has not been processed yet"}), 400

    frames = queries.get_video_frames_breakdown(db, video_id)
    
    return jsonify({
        "video_id": video_id,
        "total_frames": len(frames),
        "frames": frames
    }), 200


@video_bp.route("/<int:video_id>/all-detections", methods=["GET"])
@log_request_response
def get_all_video_detections(video_id: int):
    """Return all detections for the entire video grouped by frame."""
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    # Get all detections grouped by frame
    detections = queries.get_video_detections(db, video_id)
    
    return jsonify(detections), 200


@video_bp.route("/<int:video_id>/playback", methods=["GET"])
@log_request_response
def get_video_playback(video_id: int):
    """
    Stream annotated video with bounding boxes.
    
    Returns the pre-generated annotated video file with bounding boxes burned into frames.
    The annotated video is generated during video processing and stored in the database.
    
    Returns:
        200 OK: Annotated video file stream
        404 Not Found: Video not found or annotated video missing
        400 Bad Request: Video not processed yet
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.4, 8.5
    """
    from flask import send_file
    
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    # Check if video has been processed
    if video.get("status") != "processed":
        return jsonify({"error": "Video has not been processed yet"}), 400

    # Get annotated video path from database
    annotated_path = queries.get_annotated_video_path(db, video_id)
    
    if annotated_path is None:
        return jsonify({"error": "Annotated video file missing - video may need reprocessing"}), 404
    
    # Verify annotated video file exists at the stored path
    if not os.path.exists(annotated_path):
        return jsonify({"error": "Annotated video file not found on disk"}), 404
    
    # Determine MIME type based on file extension
    ext = annotated_path.rsplit('.', 1)[-1].lower() if '.' in annotated_path else 'mp4'
    mimetype_map = {
        'mp4': 'video/mp4',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'mkv': 'video/x-matroska'
    }
    mimetype = mimetype_map.get(ext, 'video/mp4')
    
    # Stream annotated video file
    return send_file(
        annotated_path,
        mimetype=mimetype,
        as_attachment=False,
        download_name=f"video_{video_id}_annotated.{ext}"
    )


@video_bp.route("/<int:video_id>/file", methods=["GET"])
@log_request_response
def get_video_file(video_id: int):
    """Stream the original video file for playback."""
    from flask import send_file
    
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    if video is None:
        return jsonify({"error": "Video not found"}), 404

    file_path = video["file_path"]
    if not os.path.exists(file_path):
        return jsonify({"error": "Video file not found on disk"}), 404

    # Determine mimetype based on file extension
    ext = file_path.rsplit('.', 1)[-1].lower()
    mimetype_map = {
        'mp4': 'video/mp4',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'mkv': 'video/x-matroska'
    }
    mimetype = mimetype_map.get(ext, 'video/mp4')

    # Return video file for streaming
    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=False,
        download_name=video["filename"]
    )


# ============================================================================
# Task 6: Video Operations API Endpoints
# ============================================================================

@video_bp.route("/<int:video_id>", methods=["GET"])
@log_request_response
def get_video_metadata(video_id: int):
    """
    Task 6.3: GET /api/video/{video_id} - Retrieve video metadata.
    
    Returns video metadata including filename, duration, resolution, processing status,
    and reprocessing information.
    
    Returns:
        200 OK: Video metadata
        404 Not Found: Video does not exist
    """
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    # Format datetime fields
    response = {
        "id": video["id"],
        "filename": video["filename"],
        "duration": video.get("duration_seconds"),
        "frame_count": video.get("frame_count"),
        "fps": video.get("fps"),
        "resolution": [video.get("width"), video.get("height")],
        "uploaded_at": video["uploaded_at"].isoformat() if video.get("uploaded_at") else None,
        "processed_at": video.get("last_processed_at").isoformat() if video.get("last_processed_at") else None,
        "reprocessed_at": video.get("reprocessed_at").isoformat() if video.get("reprocessed_at") else None,
        "model_version": video.get("model_version"),
        "status": video["status"]
    }
    
    return jsonify(response), 200


@video_bp.route("/<int:video_id>", methods=["DELETE"])
@log_request_response
def delete_video(video_id: int):
    """
    DELETE /api/videos/{video_id} - Delete a video and all associated data.
    
    Deletes:
    - Original video file from disk
    - Annotated video file from disk (if exists)
    - Video record from database
    - All associated detections (cascade)
    - All associated timeline entries (cascade)
    - All associated video jobs (cascade)
    
    Returns:
        200 OK: Video deleted successfully
        404 Not Found: Video does not exist
        500 Internal Server Error: Deletion failed
    
    Requirements: 4.6
    """
    from services.video_processor import VideoProcessorService
    
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    try:
        # Use VideoProcessorService to delete video and files
        service = VideoProcessorService(db)
        service.delete_video_with_files(video_id)
        
        return jsonify({
            "message": "Video deleted successfully",
            "video_id": video_id,
            "filename": video["filename"]
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to delete video",
            "details": str(e)
        }), 500


@video_bp.route("/<int:video_id>/process", methods=["POST"])
@log_request_response
def process_video_endpoint(video_id: int):
    """
    Task 6.2: POST /api/video/{video_id}/process - Trigger async video processing.
    
    Starts background processing job for face detection and recognition on the video.
    
    Returns:
        202 Accepted: Processing started
        404 Not Found: Video does not exist
        400 Bad Request: Video already being processed
    """
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    # Check if video is already being processed
    if video["status"] == "processing":
        return jsonify({"error": "Video is already being processed"}), 400
    
    # Create new processing job
    job_id = str(uuid.uuid4())
    queries.insert_video_job(db, job_id, video_id)
    
    # Start processing in background thread
    file_path = video["file_path"]
    threading.Thread(
        target=process_video,
        args=(video_id, job_id, file_path, db),
        daemon=True,
    ).start()
    
    return jsonify({
        "video_id": video_id,
        "job_id": job_id,
        "status": "processing",
        "message": "Video processing started"
    }), 202


@video_bp.route("/<int:video_id>/detections", methods=["GET"])
@log_request_response
def get_video_detections_at_timestamp(video_id: int):
    """
    Task 6.4: GET /api/video/{video_id}/detections - Get detections at timestamp.
    
    Retrieves face detections for a specific timestamp with tolerance window.
    Used by the frontend Detection Overlay component.
    
    Query Parameters:
        timestamp (float): Target timestamp in seconds
        tolerance (float, optional): Tolerance window in seconds (default: 0.25)
    
    Returns:
        200 OK: List of detections with bounding boxes and labels
        404 Not Found: Video does not exist
        400 Bad Request: Missing or invalid timestamp parameter
    """
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    # Get query parameters
    timestamp_str = request.args.get("timestamp")
    tolerance_str = request.args.get("tolerance", "0.25")
    
    if timestamp_str is None:
        return jsonify({"error": "timestamp parameter is required"}), 400
    
    try:
        timestamp = float(timestamp_str)
        tolerance = float(tolerance_str)
    except ValueError:
        return jsonify({"error": "timestamp and tolerance must be valid numbers"}), 400
    
    # Get detections from database
    detections = queries.get_detections_at_timestamp(db, video_id, timestamp, tolerance)
    
    # Format response - detections already have the correct structure from queries
    response = {
        "video_id": video_id,
        "timestamp": timestamp,
        "detections": [
            {
                "bbox": det["bbox"],  # bbox is already a dict with x1, y1, x2, y2
                "name": det["person_name"],
                "confidence": det["recognition_confidence"],
                "detection_confidence": det["detection_confidence"]
            }
            for det in detections
        ]
    }
    
    return jsonify(response), 200


@video_bp.route("/<int:video_id>/timeline", methods=["GET"])
@log_request_response
def get_video_timeline(video_id: int):
    """
    Task 6.5: GET /api/video/{video_id}/timeline - Return timeline entries.
    
    Retrieves timeline entries showing when each person appears in the video.
    Timeline entries represent continuous segments of person appearances.
    
    Returns:
        200 OK: List of timeline entries
        404 Not Found: Video does not exist
    """
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    # Get timeline entries from database
    entries = queries.get_timeline_entries(db, video_id)
    
    # Format response - map database fields to API response format
    response = {
        "video_id": video_id,
        "entries": [
            {
                "id": entry["id"],
                "person_name": entry["person_name"],
                "start_time": entry["first_appearance_time"],
                "end_time": entry["last_appearance_time"],
                "detection_count": entry["total_detections"],
                "avg_confidence": 0.0  # Not stored in DB, could be calculated if needed
            }
            for entry in entries
        ]
    }
    
    return jsonify(response), 200


@video_bp.route("/<int:video_id>/reprocess", methods=["POST"])
@log_request_response
def reprocess_video_endpoint(video_id: int):
    """
    Task 6.6: POST /api/video/{video_id}/reprocess - Trigger video reprocessing.
    
    Reprocesses video with updated model version. Deletes existing detections
    and timeline entries, then re-runs face detection and recognition.
    
    Request Body (optional):
        model_version (int): Specific model version to use (defaults to active model)
    
    Returns:
        202 Accepted: Reprocessing started
        404 Not Found: Video does not exist
        500 Internal Server Error: Reprocessing failed
    """
    from services.video_processor import VideoProcessorService
    
    db = queries.get_db_connection()
    video = queries.get_video_by_id(db, video_id)
    
    if video is None:
        return jsonify({"error": "Video not found"}), 404
    
    # Get optional model_version from request body
    body = request.get_json(silent=True) or {}
    model_version = body.get("model_version")
    
    try:
        # Create VideoProcessorService instance
        service = VideoProcessorService(db)
        
        # Trigger reprocessing in background thread
        def reprocess_async():
            try:
                service.reprocess_video(video_id, model_version)
            except Exception as e:
                import logging
                logging.error(f"Reprocessing failed for video {video_id}: {str(e)}")
        
        threading.Thread(target=reprocess_async, daemon=True).start()
        
        return jsonify({
            "video_id": video_id,
            "status": "reprocessing",
            "model_version": model_version,
            "message": "Video reprocessing started"
        }), 202
        
    except Exception as e:
        return jsonify({"error": f"Failed to start reprocessing: {str(e)}"}), 500


@video_bp.route("/reprocess-batch", methods=["POST"])
@log_request_response
def reprocess_batch_endpoint():
    """
    Task 6.7: POST /api/video/reprocess-batch - Batch reprocess multiple videos.
    
    Queues reprocessing jobs for multiple videos with optional model version.
    
    Request Body:
        video_ids (list[int]): List of video IDs to reprocess
        model_version (int, optional): Model version to use (defaults to active model)
    
    Returns:
        202 Accepted: Batch reprocessing queued
        400 Bad Request: Invalid request body
    """
    from services.video_processor import VideoProcessorService
    
    body = request.get_json(force=True) or {}
    video_ids = body.get("video_ids", [])
    model_version = body.get("model_version")
    
    if not video_ids or not isinstance(video_ids, list):
        return jsonify({"error": "video_ids must be a non-empty list"}), 400
    
    db = queries.get_db_connection()
    
    # Generate batch job ID
    batch_job_id = f"reprocess-batch-{uuid.uuid4()}"
    
    # Start reprocessing for each video in background
    def reprocess_batch_async():
        service = VideoProcessorService(db)
        for video_id in video_ids:
            try:
                service.reprocess_video(video_id, model_version)
            except Exception as e:
                import logging
                logging.error(f"Failed to reprocess video {video_id}: {str(e)}")
    
    threading.Thread(target=reprocess_batch_async, daemon=True).start()
    
    return jsonify({
        "job_id": batch_job_id,
        "video_count": len(video_ids),
        "status": "queued",
        "message": f"Batch reprocessing queued for {len(video_ids)} videos"
    }), 202
