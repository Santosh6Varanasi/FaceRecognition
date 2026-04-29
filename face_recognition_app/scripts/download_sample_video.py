#!/usr/bin/env python3
"""
Download a royalty-free sample video containing visible human faces
for use in end-to-end testing of the video face recognition feature.

Usage:
    python scripts/download_sample_video.py

Output:
    face_recognition_app/sample_data/sample_video.mp4

The script:
1. Downloads a short, publicly available video from a stable URL.
2. Saves it to sample_data/sample_video.mp4.
3. Verifies the file is a valid video using OpenCV.
4. Prints the file path and SHA-256 hash to stdout.
5. Exits with code 1 and an error message if anything fails.
"""

import hashlib
import os
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Pexels free video — "People Walking" (royalty-free, no attribution required)
# This is a stable direct-download link to a short MP4 with visible faces.
SAMPLE_VIDEO_URL = (
    "https://www.pexels.com/download/video/854671/"
    "?fps=25.0&h=720&w=1280"
)

# Fallback: Wikimedia Commons public domain clip
FALLBACK_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/transcoded/"
    "2/22/Polar_orbit.ogv/Polar_orbit.ogv.360p.webm"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "sample_data")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "sample_video.mp4")


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_video(path: str) -> None:
    """Verify the file is a valid video using OpenCV. Exits on failure."""
    try:
        import cv2  # type: ignore
    except ImportError:
        print("WARNING: opencv-python not installed — skipping video validation.")
        return

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"ERROR: OpenCV cannot open '{path}'. The file may be corrupt.", file=sys.stderr)
        sys.exit(1)

    ret, _ = cap.read()
    cap.release()

    if not ret:
        print(f"ERROR: OpenCV opened '{path}' but could not read any frames.", file=sys.stderr)
        sys.exit(1)


def download(url: str, dest: str) -> None:
    """Download url to dest with a progress indicator."""
    print(f"Downloading: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 65536
        with open(dest, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  {pct}% ({downloaded // 1024} KB / {total // 1024} KB)", end="", flush=True)
    print()  # newline after progress


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Try primary URL, fall back to secondary on failure
    for url in [SAMPLE_VIDEO_URL, FALLBACK_URL]:
        try:
            download(url, OUTPUT_PATH)
            break
        except Exception as exc:
            print(f"WARNING: Download from {url} failed: {exc}", file=sys.stderr)
            if os.path.exists(OUTPUT_PATH):
                os.remove(OUTPUT_PATH)
    else:
        print("ERROR: All download sources failed. Check your internet connection.", file=sys.stderr)
        sys.exit(1)

    # Validate
    print("Validating video file...")
    verify_video(OUTPUT_PATH)

    # Report
    file_hash = sha256_of_file(OUTPUT_PATH)
    file_size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)

    print(f"\n✓ Sample video saved successfully.")
    print(f"  Path:   {OUTPUT_PATH}")
    print(f"  Size:   {file_size_mb:.1f} MB")
    print(f"  SHA256: {file_hash}")
    print()
    print("Next steps:")
    print("  1. Start all services (see LOCAL_TESTING.md)")
    print("  2. Open http://localhost:4200/video")
    print("  3. Upload sample_data/sample_video.mp4")
    print("  4. Wait for processing to complete")
    print("  5. Go to Unknown Faces and label detected faces")
    print("  6. Retrain the model in Model Management")
    print("  7. Re-upload the same video to see named bounding boxes")


if __name__ == "__main__":
    main()
