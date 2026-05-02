"""
Stream routes — video session management and per-frame inference.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import base64
import uuid
from datetime import datetime

import numpy as np
from flask import Blueprint, jsonify, request

from db import queries
from services import inference_service
from middleware.logging_middleware import log_request_response

stream_bp = Blueprint("stream_bp", __name__, url_prefix="/api/stream")


@stream_bp.route("/session/start", methods=["POST"])
@log_request_response
def start_session():
    """Create a new video session and return its UUID."""
    db = queries.get_db_connection()
    session_id = str(uuid.uuid4())
    queries.insert_video_session(db, session_id)
    return jsonify({"session_id": session_id}), 201


@stream_bp.route("/session/end", methods=["POST"])
@log_request_response
def end_session():
    """Mark a video session as ended with total frame count."""
    body = request.get_json(force=True) or {}
    session_id = body.get("session_id")
    total_frames = body.get("total_frames", 0)

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    db = queries.get_db_connection()
    queries.end_video_session(db, session_id, datetime.utcnow(), total_frames)
    return jsonify({"success": True}), 200


@stream_bp.route("/frame", methods=["POST"])
@log_request_response
def process_frame():
    """Decode a base64 JPEG frame and run face inference."""
    body = request.get_json(force=True) or {}
    frame_data = body.get("frame_data")
    session_id = body.get("session_id")

    if not frame_data:
        return jsonify({"error": "frame_data is required"}), 400
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    # Decode base64 → numpy BGR array
    try:
        img_bytes = base64.b64decode(frame_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        import cv2
        frame_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame_bgr is None:
            raise ValueError("cv2.imdecode returned None")
    except Exception:
        return jsonify({"error": "Invalid base64 image data"}), 400

    db = queries.get_db_connection()
    result = inference_service.run_inference(frame_bgr, session_id, db)

    return jsonify({
        "detections": result["detections"],
        "frame_id": result["frame_id"],
        "processing_time_ms": result["processing_time_ms"],
    }), 200
