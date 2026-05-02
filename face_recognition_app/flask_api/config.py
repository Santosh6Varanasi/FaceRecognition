"""
Flask API Configuration — reads environment variables with defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    RECOGNITION_MODEL: str = os.environ.get("RECOGNITION_MODEL", "ArcFace")
    DETECTOR_BACKEND: str = os.environ.get("DETECTOR_BACKEND", "mtcnn")
    SVM_CONFIDENCE_THRESHOLD: float = float(
        os.environ.get("SVM_CONFIDENCE_THRESHOLD", "0.50")
    )
    FLASK_PORT: int = int(os.environ.get("FLASK_PORT", "5000"))
    UNKNOWN_FACE_IMAGES_DIR: str = os.environ.get(
        "UNKNOWN_FACE_IMAGES_DIR", "./unknown_face_images"
    )
    LABELED_FACE_IMAGES_DIR: str = os.environ.get(
        "LABELED_FACE_IMAGES_DIR", "./labeled_face_images"
    )
    TRAINING_IMAGES_DIR: str = os.environ.get(
        "TRAINING_IMAGES_DIR", "/app/training_images"
    )
    MAX_CONTENT_LENGTH: int = int(
        os.environ.get("MAX_CONTENT_LENGTH", str(100 * 1024 * 1024))  # 100MB default
    )
    TRAINING_DETECTOR_BACKEND: str = os.environ.get(
        "TRAINING_DETECTOR_BACKEND", "mtcnn"
    )
    VALIDATION_CACHE_TTL: int = int(os.environ.get("VALIDATION_CACHE_TTL", "3600"))
    
    # CORS Configuration
    CORS_ORIGINS: str = os.environ.get(
        "CORS_ORIGINS", 
        "http://localhost:4200,http://localhost:3000,http://localhost:5000"
    )
    CORS_METHODS: str = os.environ.get(
        "CORS_METHODS",
        "GET,POST,PUT,DELETE,OPTIONS"
    )
    CORS_HEADERS: str = os.environ.get(
        "CORS_HEADERS",
        "Content-Type,Authorization,X-Correlation-ID"
    )
    CORS_MAX_AGE: int = int(os.environ.get("CORS_MAX_AGE", "86400"))
    
    @property
    def cors_origins_list(self):
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def cors_methods_list(self):
        """Return CORS methods as a list."""
        return [method.strip() for method in self.CORS_METHODS.split(",")]
    
    @property
    def cors_headers_list(self):
        """Return CORS headers as a list."""
        return [header.strip() for header in self.CORS_HEADERS.split(",")]


config = Config()
