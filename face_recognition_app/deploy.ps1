# Face Recognition Application - Deployment Script
# Run this script to verify prerequisites and deploy the application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Face Recognition App - Deployment Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allChecksPass = $true

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "  ✓ Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    $allChecksPass = $false
}

# Check Docker Compose
Write-Host "Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version 2>&1
    Write-Host "  ✓ Docker Compose installed: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker Compose not found." -ForegroundColor Red
    $allChecksPass = $false
}

# Check if Docker is running
Write-Host "Checking if Docker is running..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "  ✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    $allChecksPass = $false
}

# Check PostgreSQL
Write-Host "Checking PostgreSQL..." -ForegroundColor Yellow
$psqlPath = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
if (Test-Path $psqlPath) {
    try {
        $pgVersion = & $psqlPath --version 2>&1
        Write-Host "  ✓ PostgreSQL installed: $pgVersion" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ PostgreSQL found but not responding" -ForegroundColor Red
        $allChecksPass = $false
    }
} else {
    Write-Host "  ✗ PostgreSQL not found at $psqlPath" -ForegroundColor Red
    $allChecksPass = $false
}

# Check if database exists
Write-Host "Checking database 'face_recognition'..." -ForegroundColor Yellow
try {
    $dbCheck = & $psqlPath -U postgres -d face_recognition -c "SELECT 1" 2>&1
    if ($dbCheck -match "1 row") {
        Write-Host "  ✓ Database 'face_recognition' exists and is accessible" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Database 'face_recognition' not found or not accessible" -ForegroundColor Red
        Write-Host "    Run: psql -U postgres -c 'CREATE DATABASE face_recognition;'" -ForegroundColor Yellow
        $allChecksPass = $false
    }
} catch {
    Write-Host "  ✗ Cannot connect to PostgreSQL" -ForegroundColor Red
    $allChecksPass = $false
}

# Check pgvector extension
Write-Host "Checking pgvector extension..." -ForegroundColor Yellow
try {
    $vectorCheck = & $psqlPath -U postgres -d face_recognition -c "SELECT * FROM pg_extension WHERE extname='vector'" 2>&1
    if ($vectorCheck -match "vector") {
        Write-Host "  ✓ pgvector extension is installed" -ForegroundColor Green
    } else {
        Write-Host "  ✗ pgvector extension not found" -ForegroundColor Red
        Write-Host "    Run: psql -U postgres -d face_recognition -c 'CREATE EXTENSION vector;'" -ForegroundColor Yellow
        $allChecksPass = $false
    }
} catch {
    Write-Host "  ✗ Cannot check pgvector extension" -ForegroundColor Red
    $allChecksPass = $false
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✓ Node.js installed: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Node.js not found. Please install Node.js 18+ from nodejs.org" -ForegroundColor Red
    $allChecksPass = $false
}

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found. Please install Python 3.11" -ForegroundColor Red
    $allChecksPass = $false
}

# Check ports
Write-Host "Checking port availability..." -ForegroundColor Yellow
$ports = @(5000, 3000, 4200)
foreach ($port in $ports) {
    $portCheck = netstat -ano | Select-String ":$port "
    if ($portCheck) {
        Write-Host "  ✗ Port $port is in use" -ForegroundColor Red
        $allChecksPass = $false
    } else {
        Write-Host "  ✓ Port $port is available" -ForegroundColor Green
    }
}

# Check if unknown_face_images directory exists
Write-Host "Checking unknown_face_images directory..." -ForegroundColor Yellow
if (Test-Path "unknown_face_images") {
    Write-Host "  ✓ unknown_face_images directory exists" -ForegroundColor Green
} else {
    Write-Host "  ! Creating unknown_face_images directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "unknown_face_images" | Out-Null
    Write-Host "  ✓ unknown_face_images directory created" -ForegroundColor Green
}

# Check if video_uploads directory exists
Write-Host "Checking video_uploads directory..." -ForegroundColor Yellow
if (Test-Path "flask_api/video_uploads") {
    Write-Host "  ✓ flask_api/video_uploads directory exists" -ForegroundColor Green
} else {
    Write-Host "  ! Creating flask_api/video_uploads directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "flask_api/video_uploads" | Out-Null
    Write-Host "  ✓ flask_api/video_uploads directory created" -ForegroundColor Green
}

# Check critical files
Write-Host "Checking critical files..." -ForegroundColor Yellow
$criticalFiles = @(
    "docker-compose.yml",
    "flask_api/Dockerfile",
    "flask_api/app.py",
    "flask_api/requirements.txt",
    "flask_api/routes/video.py",
    "flask_api/services/video_processor.py",
    "nextjs_backend/Dockerfile",
    "nextjs_backend/package.json",
    "angular_frontend/Dockerfile",
    "angular_frontend/package.json",
    "angular_frontend/nginx.conf"
)

$missingFiles = @()
foreach ($file in $criticalFiles) {
    if (!(Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -eq 0) {
    Write-Host "  ✓ All critical files present" -ForegroundColor Green
} else {
    Write-Host "  ✗ Missing files:" -ForegroundColor Red
    foreach ($file in $missingFiles) {
        Write-Host "    - $file" -ForegroundColor Red
    }
    $allChecksPass = $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($allChecksPass) {
    Write-Host "✓ All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to deploy. Run:" -ForegroundColor Cyan
    Write-Host "  docker-compose up --build" -ForegroundColor White
    Write-Host ""
    
    $deploy = Read-Host "Start deployment now? (y/n)"
    if ($deploy -eq "y" -or $deploy -eq "Y") {
        Write-Host ""
        Write-Host "Starting deployment..." -ForegroundColor Cyan
        Write-Host "This will take 10-15 minutes on first run (downloading ML models)..." -ForegroundColor Yellow
        Write-Host ""
        docker-compose up --build
    }
} else {
    Write-Host "✗ Some checks failed. Please fix the issues above before deploying." -ForegroundColor Red
    Write-Host ""
    Write-Host "See DEPLOYMENT.md for detailed instructions." -ForegroundColor Yellow
}

Write-Host "========================================" -ForegroundColor Cyan
