# Deployment Guide

This guide covers deploying the Face Recognition Application to production environments.

## 📋 Pre-Deployment Checklist

- [ ] Database backup completed
- [ ] Environment variables configured
- [ ] SSL certificates obtained
- [ ] Domain name configured
- [ ] Server resources verified (CPU, RAM, Storage)
- [ ] Dependencies installed on production server
- [ ] Firewall rules configured
- [ ] Model trained and tested

## 🌐 Deployment Options

### Option 1: Traditional Server Deployment

#### Requirements
- Ubuntu 20.04+ or similar Linux distribution
- 4GB RAM minimum (8GB recommended)
- 20GB storage
- PostgreSQL 12+
- Nginx
- Python 3.8+
- Node.js 16+

#### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv postgresql nginx nodejs npm

# Install build tools for face_recognition
sudo apt install -y build-essential cmake
sudo apt install -y libopenblas-dev liblapack-dev
sudo apt install -y libx11-dev libgtk-3-dev
```

#### Step 2: Database Setup

```bash
# Create database user
sudo -u postgres createuser --interactive --pwprompt face_recognition_user

# Create database
sudo -u postgres createdb -O face_recognition_user face_recognition_prod

# Run database schema
psql -U face_recognition_user -d face_recognition_prod -f face_recognition_app/database/CREATE_ALL_FRESH.sql
```

#### Step 3: Backend Deployment

```bash
# Create application directory
sudo mkdir -p /var/www/face_recognition
sudo chown $USER:$USER /var/www/face_recognition

# Copy application files
cp -r face_recognition_app /var/www/face_recognition/

# Create virtual environment
cd /var/www/face_recognition/face_recognition_app/flask_api
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create production environment file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=face_recognition_prod
DB_USER=face_recognition_user
DB_PASSWORD=your_secure_password
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
EOF

# Set proper permissions
chmod 600 .env
```

#### Step 4: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/face-recognition-api.service
```

Add the following content:

```ini
[Unit]
Description=Face Recognition Flask API
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/face_recognition/face_recognition_app/flask_api
Environment="PATH=/var/www/face_recognition/face_recognition_app/flask_api/venv/bin"
ExecStart=/var/www/face_recognition/face_recognition_app/flask_api/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    --timeout 300 \
    --access-logfile /var/log/face-recognition/access.log \
    --error-logfile /var/log/face-recognition/error.log \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/face-recognition
sudo chown www-data:www-data /var/log/face-recognition

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable face-recognition-api
sudo systemctl start face-recognition-api

# Check status
sudo systemctl status face-recognition-api
```

#### Step 5: Frontend Deployment

```bash
# Build Angular application
cd /var/www/face_recognition/face_recognition_app/angular_frontend
npm install
npm run build --prod

# Copy build to nginx directory
sudo mkdir -p /var/www/html/face-recognition
sudo cp -r dist/face-recognition-angular/* /var/www/html/face-recognition/
```

#### Step 6: Nginx Configuration

```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/face-recognition
```

Add the following content:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /var/www/html/face-recognition;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for video processing
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Increase max body size for video uploads
        client_max_body_size 500M;
    }

    # Static files (videos, images)
    location /uploads/ {
        alias /var/www/face_recognition/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/face-recognition /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

#### Step 7: SSL Configuration (Let's Encrypt)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Option 2: Docker Deployment

#### Step 1: Create Dockerfile for Backend

```dockerfile
# face_recognition_app/flask_api/Dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "300", "app:app"]
```

#### Step 2: Create Dockerfile for Frontend

```dockerfile
# face_recognition_app/angular_frontend/Dockerfile
FROM node:16 AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build --prod

FROM nginx:alpine
COPY --from=build /app/dist/face-recognition-angular /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Step 3: Create Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: face_recognition
      POSTGRES_USER: face_recognition_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./face_recognition_app/database:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  backend:
    build: ./face_recognition_app/flask_api
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: face_recognition
      DB_USER: face_recognition_user
      DB_PASSWORD: ${DB_PASSWORD}
      FLASK_ENV: production
    volumes:
      - ./uploads:/app/uploads
      - ./face_recognition_app/models:/app/models
    ports:
      - "5000:5000"
    depends_on:
      - postgres

  frontend:
    build: ./face_recognition_app/angular_frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

#### Step 4: Deploy with Docker

```bash
# Create .env file
cat > .env << EOF
DB_PASSWORD=your_secure_password
EOF

# Build and start containers
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop containers
docker-compose down
```

## 🔒 Security Considerations

### 1. Environment Variables

Never commit sensitive data. Use environment variables:

```bash
# Production .env
DB_PASSWORD=strong_random_password
SECRET_KEY=long_random_secret_key
JWT_SECRET=another_random_secret
```

### 2. Database Security

```sql
-- Restrict database user permissions
REVOKE ALL ON DATABASE face_recognition FROM PUBLIC;
GRANT CONNECT ON DATABASE face_recognition TO face_recognition_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO face_recognition_user;
```

### 3. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 4. File Permissions

```bash
# Restrict access to sensitive files
chmod 600 .env
chmod 600 face_recognition_app/models/*.pkl
chmod 755 uploads/
```

## 📊 Monitoring

### Application Logs

```bash
# Backend logs
sudo journalctl -u face-recognition-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Database Monitoring

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check database size
SELECT pg_size_pretty(pg_database_size('face_recognition'));

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 🔄 Backup and Recovery

### Database Backup

```bash
# Create backup
pg_dump -U face_recognition_user -d face_recognition_prod > backup_$(date +%Y%m%d).sql

# Automated daily backup
cat > /etc/cron.daily/face-recognition-backup << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/face-recognition
mkdir -p $BACKUP_DIR
pg_dump -U face_recognition_user face_recognition_prod | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz
# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /etc/cron.daily/face-recognition-backup
```

### Model Backup

```bash
# Backup models
tar -czf models_backup_$(date +%Y%m%d).tar.gz face_recognition_app/models/
```

### Restore from Backup

```bash
# Restore database
psql -U face_recognition_user -d face_recognition_prod < backup_20260429.sql

# Restore models
tar -xzf models_backup_20260429.tar.gz
```

## 🚀 Performance Optimization

### 1. Database Optimization

```sql
-- Create additional indexes for performance
CREATE INDEX CONCURRENTLY idx_video_detections_video_timestamp 
ON video_detections(video_id, timestamp);

CREATE INDEX CONCURRENTLY idx_unknown_faces_status_created 
ON unknown_faces(status, created_at DESC);

-- Analyze tables
ANALYZE videos;
ANALYZE video_detections;
ANALYZE unknown_faces;
```

### 2. Gunicorn Workers

Adjust workers based on CPU cores:

```bash
# Formula: (2 x CPU cores) + 1
# For 4 cores: (2 x 4) + 1 = 9 workers
gunicorn --workers 9 --bind 0.0.0.0:5000 app:app
```

### 3. Nginx Caching

```nginx
# Add to nginx configuration
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m;

location /api/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    # ... rest of proxy configuration
}
```

## 📈 Scaling

### Horizontal Scaling

1. **Load Balancer**: Use Nginx or HAProxy
2. **Multiple Backend Instances**: Run multiple Flask instances
3. **Shared Storage**: Use NFS or S3 for uploads
4. **Database Replication**: PostgreSQL streaming replication

### Vertical Scaling

1. **Increase RAM**: For better model performance
2. **Add CPU Cores**: For parallel video processing
3. **SSD Storage**: For faster database queries

## ✅ Post-Deployment Verification

```bash
# Check backend health
curl http://your-domain.com/api/health

# Check frontend
curl http://your-domain.com

# Check database connection
psql -U face_recognition_user -d face_recognition_prod -c "SELECT COUNT(*) FROM people;"

# Check logs for errors
sudo journalctl -u face-recognition-api --since "1 hour ago" | grep ERROR
```

## 🆘 Rollback Procedure

If deployment fails:

```bash
# Stop services
sudo systemctl stop face-recognition-api
sudo systemctl stop nginx

# Restore database
psql -U face_recognition_user -d face_recognition_prod < backup_previous.sql

# Restore previous code
cd /var/www/face_recognition
git checkout previous-stable-tag

# Restart services
sudo systemctl start face-recognition-api
sudo systemctl start nginx
```

## 📞 Support

For deployment issues, check:
- Application logs
- Nginx error logs
- PostgreSQL logs
- System resource usage (htop, df -h)
