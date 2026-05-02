"""
People routes — list and manage registered people.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, jsonify, request

from db import queries
from middleware.logging_middleware import log_request_response

people_bp = Blueprint("people_bp", __name__, url_prefix="/api/people")


@people_bp.route("", methods=["GET"])
@people_bp.route("/", methods=["GET"])
@log_request_response
def list_people():
    """
    GET /api/people - List all registered people with face counts.
    
    Returns a list of all people in the system with their face counts,
    ordered alphabetically by name.
    
    Returns:
        200 OK: List of people with metadata
    """
    db = queries.get_db_connection()
    people = queries.get_people_with_face_counts(db)
    
    # Format datetime fields to ISO format
    for person in people:
        if person.get('created_at'):
            person['created_at'] = person['created_at'].isoformat()
    
    return jsonify(people), 200


@people_bp.route("", methods=["POST"])
@people_bp.route("/", methods=["POST"])
@log_request_response
def add_person():
    """
    POST /api/people - Add a new person to the system.
    
    Request Body:
        name (str, required): Person's name
        description (str, optional): Description or notes
        role (str, optional): Person's role or title
    
    Returns:
        201 Created: Person created successfully
        400 Bad Request: Invalid request body
    """
    body = request.get_json(force=True) or {}
    name = body.get('name', '').strip()
    description = body.get('description')
    role = body.get('role')
    
    if not name:
        return jsonify({'error': 'name is required'}), 400
    
    db = queries.get_db_connection()
    
    try:
        person = queries.insert_person(db, name, description, role)
        
        # Format datetime to ISO format
        if person.get('created_at'):
            person['created_at'] = person['created_at'].isoformat()
        
        # Add face_count field (new person has 0 faces)
        person['face_count'] = 0
        
        return jsonify(person), 201
    except Exception as e:
        return jsonify({'error': f'Failed to create person: {str(e)}'}), 500
