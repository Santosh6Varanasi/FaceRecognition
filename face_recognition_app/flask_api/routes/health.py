"""
Health check blueprint — GET /api/health
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, jsonify

import model_cache
from db.queries import get_db_connection
from middleware.logging_middleware import log_request_response

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
@log_request_response
def health():
    model_loaded = model_cache.is_model_loaded()
    active_model_version = model_cache.get_cached_version()

    db_connected = False
    try:
        db = get_db_connection()
        raw = db.get_connection()
        try:
            cursor = raw.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            db_connected = True
        finally:
            db.return_connection(raw)
        db.close_all()
    except Exception:
        db_connected = False

    return jsonify(
        {
            "status": "ok",
            "model_loaded": model_loaded,
            "active_model_version": active_model_version,
            "db_connected": db_connected,
        }
    )
