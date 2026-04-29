"""
Unknown faces routes — review, label, reject, and bulk-label unknown detections.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, jsonify, request

from db import queries
from services import image_service

unknown_faces_bp = Blueprint("unknown_faces_bp", __name__, url_prefix="/api")


@unknown_faces_bp.route("/unknown-faces", methods=["GET"])
def list_unknown_faces():
    """Return a paginated list of unknown faces."""
    status = request.args.get("status", "pending")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    db = queries.get_db_connection()
    items, total = queries.get_unknown_faces_paginated(db, status, page, page_size)

    for item in items:
        item["thumbnail_url"] = f"/api/unknown-faces/{item['id']}/image"

    return jsonify({
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }), 200


@unknown_faces_bp.route("/unknown-faces/<int:face_id>/image", methods=["GET"])
def get_face_image(face_id: int):
    """Serve the JPEG thumbnail for an unknown face."""
    img_bytes = image_service.load_face_image(face_id)
    if img_bytes is None:
        return jsonify({"error": "Image not found"}), 404

    from flask import Response
    return Response(img_bytes, mimetype="image/jpeg")


@unknown_faces_bp.route("/unknown-faces/<int:face_id>/label", methods=["POST"])
def label_face(face_id: int):
    """Assign a person name to an unknown face and add its embedding to training data."""
    body = request.get_json(force=True) or {}
    person_name = body.get("person_name")
    labeled_by = body.get("labeled_by", "")

    if not person_name:
        return jsonify({"error": "person_name is required"}), 400

    db = queries.get_db_connection()

    person_id = queries.upsert_person(db, person_name)
    face_record = queries.get_unknown_face_by_id(db, face_id)
    if face_record is None:
        return jsonify({"error": "Face not found"}), 404

    embedding = face_record["embedding"]
    queries.label_unknown_face(db, face_id, person_id, labeled_by)
    queries.insert_face_from_unknown(db, person_id, embedding, "unknown_labeled")

    return jsonify({"success": True}), 200


@unknown_faces_bp.route("/unknown-faces/<int:face_id>/reject", methods=["POST"])
def reject_face(face_id: int):
    """Mark an unknown face as rejected."""
    body = request.get_json(force=True) or {}
    rejected_by = body.get("rejected_by", "")

    db = queries.get_db_connection()
    queries.reject_unknown_face(db, face_id, rejected_by)
    return jsonify({"success": True}), 200


@unknown_faces_bp.route("/unknown-faces/bulk-label", methods=["POST"])
def bulk_label_faces():
    """Label multiple unknown faces in a single DB transaction."""
    body = request.get_json(force=True) or {}
    labels = body.get("labels", [])
    labeled_by = body.get("labeled_by", "")

    db = queries.get_db_connection()
    raw_conn = db.get_connection()

    labeled_count = 0
    failed_ids = []

    try:
        cursor = raw_conn.cursor()

        for entry in labels:
            face_id = entry.get("id")
            person_name = entry.get("person_name")
            if face_id is None or not person_name:
                failed_ids.append(face_id)
                continue

            try:
                # Upsert person
                cursor.execute("SELECT id FROM people WHERE name = %s", (person_name,))
                row = cursor.fetchone()
                if row:
                    person_id = row[0]
                else:
                    cursor.execute(
                        "INSERT INTO people (name) VALUES (%s) RETURNING id",
                        (person_name,),
                    )
                    person_id = cursor.fetchone()[0]

                # Get face embedding
                cursor.execute(
                    "SELECT embedding FROM unknown_faces WHERE id = %s", (face_id,)
                )
                face_row = cursor.fetchone()
                if face_row is None:
                    failed_ids.append(face_id)
                    continue
                embedding = face_row[0]

                # Label the unknown face
                cursor.execute(
                    "UPDATE unknown_faces SET status = 'labeled', "
                    "assigned_person_id = %s, labeled_by_user = %s, "
                    "labeled_at = NOW(), updated_at = NOW() WHERE id = %s",
                    (person_id, labeled_by, face_id),
                )

                # Insert into faces table
                cursor.execute(
                    "INSERT INTO faces (person_id, image_path, embedding, source_type) "
                    "VALUES (%s, %s, %s::vector, %s)",
                    (person_id, "", embedding, "unknown_labeled"),
                )

                labeled_count += 1

            except Exception:
                failed_ids.append(face_id)
                continue

        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        db.return_connection(raw_conn)

    return jsonify({"labeled_count": labeled_count, "failed_ids": failed_ids}), 200


# ============================================================================
# Task 7: Bulk Operations and Model Management API Endpoints
# ============================================================================

@unknown_faces_bp.route("/unknown-faces/bulk-delete", methods=["POST"])
def bulk_delete_unknown_faces():
    """
    Task 7.1: POST /api/unknown-faces/bulk-delete - Bulk delete unknown faces.
    
    Deletes all unknown faces matching the filter status. Uses BulkOperationHandler
    service for transaction-safe bulk operations.
    
    Request Body:
        filter_status (str, optional): Filter by status - "all", "pending", "labeled", "rejected"
                                       Defaults to "all" if not provided
    
    Returns:
        200 OK: Bulk operation result with success/failure counts
        500 Internal Server Error: Operation failed
    """
    from services.bulk_operations import BulkOperationHandler
    
    body = request.get_json(silent=True) or {}
    filter_status = body.get("filter_status", "all")
    
    db = queries.get_db_connection()
    handler = BulkOperationHandler(db)
    
    try:
        result = handler.bulk_delete(filter_status)
        return jsonify({
            "operation_type": "delete",
            "affected_count": result["total_count"],
            "success_count": result["success_count"],
            "failed_count": result["failure_count"],
            "failed_ids": [],
            "execution_time": 0.0,
            "message": result["message"]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Bulk delete failed: {str(e)}"}), 500


@unknown_faces_bp.route("/unknown-faces/bulk-reject", methods=["POST"])
def bulk_reject_unknown_faces():
    """
    Task 7.2: POST /api/unknown-faces/bulk-reject - Bulk reject unknown faces.
    
    Marks all unknown faces matching the filter status as rejected. Uses
    BulkOperationHandler service for transaction-safe bulk operations.
    
    Request Body:
        filter_status (str, optional): Filter by status - "all", "pending", "labeled", "rejected"
                                       Defaults to "all" if not provided
    
    Returns:
        200 OK: Bulk operation result with success/failure counts
        500 Internal Server Error: Operation failed
    """
    from services.bulk_operations import BulkOperationHandler
    
    body = request.get_json(silent=True) or {}
    filter_status = body.get("filter_status", "all")
    
    db = queries.get_db_connection()
    handler = BulkOperationHandler(db)
    
    try:
        result = handler.bulk_reject(filter_status)
        return jsonify({
            "operation_type": "reject",
            "affected_count": result["total_count"],
            "success_count": result["success_count"],
            "failed_count": result["failure_count"],
            "failed_ids": [],
            "execution_time": 0.0,
            "message": result["message"]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Bulk reject failed: {str(e)}"}), 500


@unknown_faces_bp.route("/unknown-faces/count", methods=["GET"])
def get_unknown_faces_count():
    """
    Task 7.3: GET /api/unknown-faces/count - Get count of unknown faces.
    
    Returns the count of unknown faces matching the filter status.
    Used for preview before bulk operations.
    
    Query Parameters:
        filter_status (str, optional): Filter by status - "all", "pending", "labeled", "rejected"
                                       Defaults to "all" if not provided
    
    Returns:
        200 OK: Count of faces matching filter
    """
    from services.bulk_operations import BulkOperationHandler
    
    filter_status = request.args.get("filter_status", "all")
    
    db = queries.get_db_connection()
    handler = BulkOperationHandler(db)
    
    try:
        count = handler.get_affected_count(filter_status)
        return jsonify({
            "filter_status": filter_status,
            "count": count
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get count: {str(e)}"}), 500
