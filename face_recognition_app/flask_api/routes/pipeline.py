"""
Pipeline routes — run the full embedding generation + SVM training pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import threading
import traceback

from flask import Blueprint, jsonify, request

from db import queries
from job_registry import create_job, update_job
from services import retraining_service

logger = logging.getLogger(__name__)

pipeline_bp = Blueprint("pipeline_bp", __name__, url_prefix="/api/pipeline")


def _run_full_pipeline(job_id: str, db) -> None:
    """
    Background worker: optionally run Section C (embedding generation)
    then run the full SVM training pipeline (Section D equivalent).
    """
    try:
        update_job(job_id, status="running", progress_pct=10, message="Starting pipeline...")

        # Step 1 — Section C: generate embeddings if available
        try:
            import importlib
            section_c = importlib.import_module("section_c_generate_embeddings")
            from config import config as _config

            update_job(job_id, progress_pct=20, message="Generating embeddings (Section C)...")
            training_dir = getattr(_config, "TRAINING_DATA_DIR", "./training_data")
            section_c.generate_and_save_embeddings(db, training_dir)
        except Exception as exc:
            logger.warning("Section C skipped or failed: %s", exc)

        # Step 2 — Section D: train SVM (reuse retraining_service pipeline)
        update_job(job_id, progress_pct=60, message="Training SVM (Section D)...")

        # Delegate to the retraining pipeline internals
        retraining_service._run_pipeline(job_id, db)

    except Exception as exc:
        logger.error("Full pipeline job %s failed:\n%s", job_id, traceback.format_exc())
        update_job(job_id, status="failed", message=str(exc))


@pipeline_bp.route("/run-full", methods=["POST"])
def run_full_pipeline():
    """
    Launch an async job that runs Section C (embedding generation) then
    Section D (SVM training). Poll status via GET /api/model/retrain/status/<job_id>.
    """
    db = queries.get_db_connection()
    job_id = create_job()
    update_job(job_id, status="running")
    thread = threading.Thread(target=_run_full_pipeline, args=(job_id, db), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id}), 202
