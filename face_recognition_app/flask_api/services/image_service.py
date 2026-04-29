"""
Image service — face crop/save and face image loading utilities.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Optional

import cv2
import numpy as np

from config import config

_FACE_SIZE = (112, 112)


def crop_and_save_face(
    frame_bgr: np.ndarray,
    bbox: dict,
    unknown_face_id: int,
) -> str:
    """
    Crop a face region from frame_bgr, resize to 112x112, and save as JPEG.

    Parameters
    ----------
    frame_bgr:
        Full BGR frame as a numpy array.
    bbox:
        Dict with keys x1, y1, x2, y2 (integer pixel coordinates).
    unknown_face_id:
        Used as the filename stem: <UNKNOWN_FACE_IMAGES_DIR>/<id>.jpg

    Returns
    -------
    str
        Absolute path to the saved JPEG file.
    """
    h, w = frame_bgr.shape[:2]

    x1 = max(0, int(bbox["x1"]))
    y1 = max(0, int(bbox["y1"]))
    x2 = min(w, int(bbox["x2"]))
    y2 = min(h, int(bbox["y2"]))

    face_crop = frame_bgr[y1:y2, x1:x2]
    face_resized = cv2.resize(face_crop, _FACE_SIZE)

    save_dir = config.UNKNOWN_FACE_IMAGES_DIR
    os.makedirs(save_dir, exist_ok=True)

    file_path = os.path.join(save_dir, f"{unknown_face_id}.jpg")
    cv2.imwrite(file_path, face_resized)

    return os.path.abspath(file_path)


def load_face_image(unknown_face_id: int) -> Optional[bytes]:
    """
    Read the saved face JPEG for the given unknown_face_id as raw bytes.

    Returns None if the file does not exist.
    """
    file_path = os.path.join(config.UNKNOWN_FACE_IMAGES_DIR, f"{unknown_face_id}.jpg")
    if not os.path.exists(file_path):
        return None
    with open(file_path, "rb") as f:
        return f.read()
