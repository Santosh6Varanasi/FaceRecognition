"""
Dashboard routes — aggregate statistics and KPIs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, jsonify

from db import queries
from middleware.logging_middleware import log_request_response

dashboard_bp = Blueprint("dashboard_bp", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@log_request_response
def get_dashboard_stats():
    """
    GET /api/dashboard/stats - Get dashboard statistics.
    
    Returns aggregate statistics for the dashboard including:
    - Total registered people
    - Total training faces
    - Pending unknown faces
    - Labeled unknown faces
    - Active model version and accuracy
    - Total detections today
    
    Returns:
        200 OK: Dashboard statistics
    """
    db = queries.get_db_connection()
    stats = queries.get_dashboard_stats(db)
    return jsonify(stats), 200
