"""
Seed script — downloads sample face images from public domain sources,
generates ArcFace embeddings, inserts them into the database, and trains
the initial SVM model.

Run from the flask_api directory:
    python seed_model.py

Uses only public-domain / CC0 images from:
- https://thispersondoesnotexist.com  (AI-generated, no real person)
- Labeled as fictional characters so there are no privacy concerns.
"""

import io
import os
import sys
import time
import urllib.parse
import urllib.request
import logging

import numpy as np
from sklearn.preprocessing import normalize, LabelEncoder
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score
import joblib

# ── path setup so local imports work ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import config
from face_recognition_app.database.db_connection import DatabaseConnection

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── DeepFace (lazy import — slow first load) ───────────────────────────────────
logger.info("Loading DeepFace models (first run may take a few minutes)...")
from deepface import DeepFace

# ── Fictional seed people — AI-generated faces, no real identities ─────────────
# Each entry: (name, list_of_image_urls)
# Using thispersondoesnotexist.com — every refresh gives a unique AI face.
# We fetch multiple times to get varied images per person.
SEED_PEOPLE = [
    "Person_Alpha",
    "Person_Beta",
    "Person_Gamma",
    "Person_Delta",
    "Person_Epsilon",
]

IMAGES_PER_PERSON = 5   # number of sample images per person
FACE_SIZE = (112, 112)


def get_db() -> DatabaseConnection:
    parsed = urllib.parse.urlparse(config.DATABASE_URL)
    return DatabaseConnection(
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        database=(parsed.path or "/face_recognition").lstrip("/"),
        user=parsed.username or "postgres",
        password=parsed.password or "postgres",
    )


def download_ai_face() -> np.ndarray:
    """
    Download one AI-generated face from thispersondoesnotexist.com.
    Returns a BGR numpy array (H, W, 3).
    """
    import cv2
    url = "https://thispersondoesnotexist.com"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        img_bytes = resp.read()
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img_bgr


def get_embedding(img_bgr: np.ndarray) -> np.ndarray | None:
    """Generate a normalised 512-d ArcFace embedding from a BGR image."""
    try:
        result = DeepFace.represent(
            img_path=img_bgr,
            model_name=config.RECOGNITION_MODEL,
            detector_backend=config.DETECTOR_BACKEND,
            enforce_detection=False,
        )
        if not result:
            return None
        emb = np.array(result[0]["embedding"], dtype=np.float64)
        return normalize(emb.reshape(1, -1), norm="l2")[0]
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return None


def upsert_person(db: DatabaseConnection, name: str) -> int:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM people WHERE name = %s", (name,))
        row = cur.fetchone()
        if row:
            logger.info("  Person '%s' already exists (id=%d)", name, row[0])
            return row[0]
        cur.execute(
            "INSERT INTO people (name, role) VALUES (%s, %s) RETURNING id",
            (name, "seed"),
        )
        pid = cur.fetchone()[0]
        conn.commit()
        logger.info("  Created person '%s' (id=%d)", name, pid)
        return pid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        db.return_connection(conn)


def insert_embedding(db: DatabaseConnection, person_id: int, embedding: np.ndarray, idx: int) -> None:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        image_path = f"seed_{person_id}_{idx}"
        cur.execute(
            "INSERT INTO faces (person_id, image_path, embedding, source_type) "
            "VALUES (%s, %s, %s::vector, 'training') "
            "ON CONFLICT (person_id, image_path) DO NOTHING",
            (person_id, image_path, embedding.tolist()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        db.return_connection(conn)


def count_existing_faces(db: DatabaseConnection, person_id: int) -> int:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM faces WHERE person_id = %s", (person_id,))
        return cur.fetchone()[0]
    finally:
        cur.close()
        db.return_connection(conn)


def load_all_embeddings(db: DatabaseConnection):
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT f.embedding, p.name FROM faces f "
            "JOIN people p ON f.person_id = p.id "
            "WHERE f.source_type IN ('training', 'unknown_labeled') "
            "ORDER BY p.id, f.id"
        )
        rows = cur.fetchall()
        X = np.array([np.array(r[0], dtype=np.float32) for r in rows])
        y = [r[1] for r in rows]
        return X, y
    finally:
        cur.close()
        db.return_connection(conn)


def get_next_version(db: DatabaseConnection) -> int:
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM model_versions")
        return cur.fetchone()[0]
    finally:
        cur.close()
        db.return_connection(conn)


def save_model_to_db(
    db: DatabaseConnection,
    svm: SVC,
    le: LabelEncoder,
    version: int,
    cv_acc: float,
    cv_std: float,
    n_samples: int,
    duration: float,
) -> None:
    import json
    model_buf = io.BytesIO()
    joblib.dump(svm, model_buf)
    le_buf = io.BytesIO()
    joblib.dump(le, le_buf)

    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE model_versions SET is_active = FALSE")
        cur.execute(
            "INSERT INTO model_versions "
            "(version_number, model_bytes, label_encoder_bytes, num_classes, "
            "num_training_samples, trained_at, training_duration_seconds, "
            "cross_validation_accuracy, cross_validation_std, svm_hyperparams, is_active) "
            "VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s::jsonb, TRUE)",
            (
                version,
                model_buf.getvalue(),
                le_buf.getvalue(),
                len(le.classes_),
                n_samples,
                duration,
                cv_acc,
                cv_std,
                json.dumps({"kernel": "rbf", "C": 10, "gamma": "scale"}),
            ),
        )
        conn.commit()
        logger.info("  Saved model version %d to database (active=TRUE)", version)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        db.return_connection(conn)


def main():
    logger.info("=" * 60)
    logger.info("Face Recognition — Seed Script")
    logger.info("=" * 60)

    db = get_db()
    logger.info("Database connected.")

    # ── Step 1: Download images and generate embeddings ───────────────────────
    logger.info("\nStep 1: Generating seed face embeddings...")
    for name in SEED_PEOPLE:
        logger.info("\nProcessing: %s", name)
        person_id = upsert_person(db, name)
        existing = count_existing_faces(db, person_id)
        needed = IMAGES_PER_PERSON - existing
        if needed <= 0:
            logger.info("  Already has %d faces — skipping download.", existing)
            continue

        inserted = 0
        attempts = 0
        while inserted < needed and attempts < needed * 3:
            attempts += 1
            try:
                img_bgr = download_ai_face()
                if img_bgr is None:
                    continue
                emb = get_embedding(img_bgr)
                if emb is None:
                    continue
                insert_embedding(db, person_id, emb, existing + inserted)
                inserted += 1
                logger.info("  [%d/%d] Embedding saved", inserted, needed)
                time.sleep(0.5)  # be polite to the server
            except Exception as exc:
                logger.warning("  Attempt %d failed: %s", attempts, exc)
                time.sleep(1)

        logger.info("  Done: %d/%d embeddings for '%s'", inserted, needed, name)

    # ── Step 2: Train SVM ─────────────────────────────────────────────────────
    logger.info("\nStep 2: Training SVM classifier...")
    X, y = load_all_embeddings(db)

    if len(X) < 2:
        logger.error("Not enough embeddings to train (need at least 2). Aborting.")
        sys.exit(1)

    unique_classes = list(set(y))
    logger.info("  Classes: %s", unique_classes)
    logger.info("  Total samples: %d", len(X))

    X_norm = normalize(X, norm="l2")
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    svm = SVC(kernel="rbf", C=10, gamma="scale", probability=True)
    n_splits = min(5, min(np.bincount(y_enc)))
    cv = StratifiedKFold(n_splits=max(2, n_splits))

    t0 = time.time()
    cv_scores = cross_val_score(svm, X_norm, y_enc, cv=cv, scoring="accuracy")
    svm.fit(X_norm, y_enc)
    duration = time.time() - t0

    cv_acc = float(np.mean(cv_scores))
    cv_std = float(np.std(cv_scores))
    logger.info("  CV accuracy: %.1f%% ± %.1f%%", cv_acc * 100, cv_std * 100)
    logger.info("  Training time: %.1fs", duration)

    # ── Step 3: Save model ────────────────────────────────────────────────────
    logger.info("\nStep 3: Saving model to database...")
    version = get_next_version(db)
    save_model_to_db(db, svm, le, version, cv_acc, cv_std, len(X), duration)

    db.close_all()

    logger.info("\n" + "=" * 60)
    logger.info("Seed complete!")
    logger.info("  Model version %d is now active.", version)
    logger.info("  Classes trained: %s", list(le.classes_))
    logger.info("  Restart Flask API to load the new model.")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("  1. Restart Flask: python app.py")
    logger.info("  2. Go to People page → Add yourself with your name")
    logger.info("  3. Camera will detect your face as 'Unknown'")
    logger.info("  4. Label it in Unknown Faces page")
    logger.info("  5. Retrain from Model Management page")


if __name__ == "__main__":
    main()
