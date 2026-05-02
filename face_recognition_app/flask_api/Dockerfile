# Flask API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and PostgreSQL
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for unknown face images
RUN mkdir -p /app/unknown_face_images && \
    mkdir -p /app/video_uploads && \
    mkdir -p /app/training_images && \
    chmod 755 /app/unknown_face_images && \
    chmod 755 /app/video_uploads && \
    chmod 755 /app/training_images

# Expose Flask port
EXPOSE 5000

# Run Flask app
CMD ["python", "app.py"]
