"""
Flask Application Factory for Face Recognition API.
"""

import logging
import os
import sys

from flask import Flask
from flask_cors import CORS

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    # Apply CORS — allow Angular dev server on all API routes
    CORS(
        app,
        origins=["http://localhost:4200", "http://localhost:3000"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=False,
        automatic_options=True,
    )

    # Ensure unknown face images directory exists
    os.makedirs(config.UNKNOWN_FACE_IMAGES_DIR, exist_ok=True)

    # Test DB connection on startup
    _check_db_connection()

    # Register blueprints
    from routes.health import health_bp
    from routes.stream import stream_bp
    from routes.unknown_faces import unknown_faces_bp
    from routes.model import model_bp
    from routes.pipeline import pipeline_bp
    from routes.video import video_bp
    from routes.training import training_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(unknown_faces_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(training_bp)
    logger.info("✅ All blueprints registered.")

    # Catch-all OPTIONS handler for preflight requests
    @app.before_request
    def handle_options():
        from flask import request as req, Response
        if req.method == "OPTIONS":
            res = Response()
            res.headers["Access-Control-Allow-Origin"] = "http://localhost:4200"
            res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            res.headers["Access-Control-Max-Age"] = "86400"
            return res

    return app


def _check_db_connection() -> None:
    """Test DB connection; exit with code 1 on failure."""
    import urllib.parse

    if not config.DATABASE_URL:
        logger.error("❌ DATABASE_URL is not set. Exiting.")
        sys.exit(1)

    try:
        import sys as _sys
        import os as _os
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
        from face_recognition_app.database.db_connection import DatabaseConnection

        parsed = urllib.parse.urlparse(config.DATABASE_URL)
        db = DatabaseConnection(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=(parsed.path or "/face_recognition").lstrip("/"),
            user=parsed.username or "admin",
            password=parsed.password or "admin",
        )
        # Quick connectivity check — get a connection and return it immediately
        conn = db.get_connection()
        db.return_connection(conn)
        db.close_all()
        logger.info("✅ Database connection verified.")
    except Exception as exc:
        logger.error(f"❌ Database connection failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app = create_app()
    app.run(port=config.FLASK_PORT)
