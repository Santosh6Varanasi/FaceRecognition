"""
Flask Application Factory for Face Recognition API.
"""

import logging
import os
import sys

from flask import Flask
from flask_cors import CORS

from config import config
from logging_config import setup_logging
from middleware.error_handler import register_error_handlers

# Basic logging until app is created
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    
    # Set maximum content length for file uploads (500MB default)
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    
    # Configure centralized logging system
    # Requirements: 13.1, 13.2, 13.3, 13.4
    app_logger = setup_logging(app)
    app_logger.info("Flask application starting...")
    app_logger.info(f"Max content length set to: {config.MAX_CONTENT_LENGTH / (1024*1024):.0f}MB")
    
    # Register error handlers
    # Requirements: 7.5
    register_error_handlers(app)

    # Apply CORS — use environment-based configuration
    CORS(
        app,
        origins=config.cors_origins_list,
        methods=config.cors_methods_list,
        allow_headers=config.cors_headers_list,
        supports_credentials=False,
        automatic_options=True,
    )

    # Ensure unknown face images directory exists
    os.makedirs(config.UNKNOWN_FACE_IMAGES_DIR, exist_ok=True)
    
    # Ensure labeled face images directory exists
    os.makedirs(config.LABELED_FACE_IMAGES_DIR, exist_ok=True)

    # Initialize shared database connection pool
    _init_db_connection_pool(app)

    # Register blueprints
    from routes.health import health_bp
    from routes.stream import stream_bp
    from routes.unknown_faces import unknown_faces_bp
    from routes.model import model_bp
    from routes.pipeline import pipeline_bp
    from routes.video import video_bp
    from routes.training import training_bp
    from routes.dashboard import dashboard_bp
    from routes.people import people_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(unknown_faces_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(pipeline_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(training_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(people_bp)
    app_logger.info("✅ All blueprints registered.")

    # Catch-all OPTIONS handler for preflight requests
    @app.before_request
    def handle_options():
        from flask import request as req, Response
        if req.method == "OPTIONS":
            res = Response()
            origin = req.headers.get("Origin")
            allowed_origins = config.cors_origins_list
            if origin in allowed_origins:
                res.headers["Access-Control-Allow-Origin"] = origin
            else:
                # Default to first origin in list
                res.headers["Access-Control-Allow-Origin"] = allowed_origins[0] if allowed_origins else "*"
            res.headers["Access-Control-Allow-Methods"] = config.CORS_METHODS
            res.headers["Access-Control-Allow-Headers"] = config.CORS_HEADERS
            res.headers["Access-Control-Max-Age"] = str(config.CORS_MAX_AGE)
            return res

    return app


def _init_db_connection_pool(app: Flask) -> None:
    """
    Initialize shared database connection pool and store in app context.
    This ensures a single connection pool is reused across all requests.
    """
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
        
        # Quick connectivity check
        conn = db.get_connection()
        db.return_connection(conn)
        
        # Store the shared connection pool in app config
        app.config['DB_CONNECTION_POOL'] = db
        logger.info("✅ Database connection pool initialized and verified.")
        
    except Exception as exc:
        logger.error(f"❌ Database connection failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    app = create_app()
    app.run(port=config.FLASK_PORT)
