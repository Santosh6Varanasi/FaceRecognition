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
    TRAINING_IMAGES_DIR: str = os.environ.get(
        "TRAINING_IMAGES_DIR", "/app/training_images"
    )
    MAX_CONTENT_LENGTH: int = int(
        os.environ.get("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024))
    )
    TRAINING_DETECTOR_BACKEND: str = os.environ.get(
        "TRAINING_DETECTOR_BACKEND", "mtcnn"
    )
    VALIDATION_CACHE_TTL: int = int(os.environ.get("VALIDATION_CACHE_TTL", "3600"))
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")


config = Config()
