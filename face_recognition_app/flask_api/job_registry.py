"""
In-memory registry for background training jobs.

Tracks job state (queued → running → completed / failed) so that the
REST API can report progress without hitting the database on every poll.
"""

import copy
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class JobState:
    job_id: str
    status: str          # 'queued' | 'running' | 'completed' | 'failed'
    progress_pct: int    # 0-100
    message: str
    version_number: Optional[int] = None
    cv_accuracy: Optional[float] = None
    num_classes: Optional[int] = None


# Module-level state
_jobs: Dict[str, JobState] = {}
_lock = threading.Lock()


def create_job() -> str:
    """
    Create a new job in 'queued' state and return its job_id.

    Returns
    -------
    str
        UUID string identifying the new job.
    """
    job_id = str(uuid.uuid4())
    state = JobState(
        job_id=job_id,
        status="queued",
        progress_pct=0,
        message="Queued",
    )
    with _lock:
        _jobs[job_id] = state
    return job_id


def update_job(job_id: str, **kwargs) -> None:
    """
    Update one or more fields of an existing JobState.

    Parameters
    ----------
    job_id:
        The job to update.
    **kwargs:
        Field names and their new values (e.g. ``status='running'``,
        ``progress_pct=50``).
    """
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)


def get_job(job_id: str) -> Optional[JobState]:
    """
    Return a shallow copy of the JobState for *job_id*, or None.

    A copy is returned so callers cannot mutate the registry directly.
    """
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return copy.copy(job)


def job_to_dict(job: JobState) -> dict:
    """
    Convert a JobState to a JSON-serialisable dict.

    Parameters
    ----------
    job:
        The JobState to serialise.

    Returns
    -------
    dict
    """
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "message": job.message,
        "version_number": job.version_number,
        "cv_accuracy": job.cv_accuracy,
        "num_classes": job.num_classes,
    }
