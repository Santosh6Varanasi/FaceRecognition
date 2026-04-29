# System Diagnostics Script
# Run this to diagnose deployment issues

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Face Recognition System Diagnostics" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$issues = @()
$warnings = @()

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.11") {
        Write-Host "✓ Python 3.11 installed: $pythonVersion" -ForegroundColor Green
    } elseif ($pythonVersion -match "Python 3\.") {
        Write-Host "⚠ Python installed but not 3.11: $pythonVersion" -ForegroundColor Yellow
        $warnings += "Python 3.11 recommended for TensorFlow compatibility"
    } else {
        Write-Host "✗ Python not found or wrong version" -ForegroundColor Red
        $issues += "Install Python 3.11"
    }
} catch {
    Write-Host "✗ Python not found in PATH" -ForegroundColor Red
    $issues += "Install Python 3.11 and add to PATH"
}

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($dockerVersion -match "Docker version") {
        Write-Host "✓ Docker installed: $dockerVersion" -ForegroundColor Green
        
        # Check if Docker daemon is running
        $dockerPs = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Docker daemon is running" -ForegroundColor Green
        } else {
            Write-Host "✗ Docker daemon not running" -ForegroundColor Red
            $issues += "Start Docker Desktop"
        }
    } else {
        Write-Host "✗ Docker not found" -ForegroundColor Red
        $issues += "Install Docker Desktop"
    }
} catch {
    Write-Host "✗ Docker not found in PATH" -ForegroundColor Red
    $issues += "Install Docker Desktop"
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    if ($nodeVersion -match "v(\d+)\.") {
        $majorVersion = [int]$matches[1]
        if ($majorVersion -ge 18) {
            Write-Host "✓ Node.js installed: $nodeVersion" -ForegroundColor Green
        } else {
            Write-Host "⚠ Node.js version too old: $nodeVersion" -ForegroundColor Yellow
            $warnings += "Node.js 18+ recommended"
        }
    } else {
        Write-Host "✗ Node.js not found" -ForegroundColor Red
        $issues += "Install Node.js 18+"
    }
} catch {
    Write-Host "✗ Node.js not found in PATH" -ForegroundColor Red
    $issues += "Install Node.js 18+"
}

# Check npm
Write-Host "Checking npm..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version 2>&1
    Write-Host "✓ npm installed: v$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ npm not found" -ForegroundColor Red
    $issues += "npm should come with Node.js"
}

# Check PostgreSQL
Write-Host "Checking PostgreSQL..." -ForegroundColor Yellow
$PSQL_PATH = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
if (Test-Path $PSQL_PATH) {
    Write-Host "✓ PostgreSQL 17 found at $PSQL_PATH" -ForegroundColor Green
    
    # Try to connect (will prompt for password)
    Write-Host "  Testing connection (enter password)..." -ForegroundColor Cyan
    $DB_PASSWORD = Read-Host "  Enter PostgreSQL password for user 'postgres'" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD)
    $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    $env:PGPASSWORD = $PlainPassword
    
    $testResult = & $PSQL_PATH -U postgres -c "SELECT version()" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ PostgreSQL connection successful" -ForegroundColor Green
        
        # Check if database exists
        $dbExists = & $PSQL_PATH -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='face_recognition'" 2>&1
        if ($dbExists -eq "1") {
            Write-Host "✓ Database 'face_recognition' exists" -ForegroundColor Green
            
            # Check pgvector
            $vectorExists = & $PSQL_PATH -U postgres -d face_recognition -tAc "SELECT 1 FROM pg_extension WHERE extname='vector'" 2>&1
            if ($vectorExists -eq "1") {
                Write-Host "✓ pgvector extension installed" -ForegroundColor Green
            } else {
                Write-Host "✗ pgvector extension not installed" -ForegroundColor Red
                $issues += "Run setup_database.ps1 to install pgvector"
            }
            
            # Check tables
            $tableCount = & $PSQL_PATH -U postgres -d face_recognition -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>&1
            if ([int]$tableCount -ge 7) {
                Write-Host "✓ Database tables created ($tableCount tables)" -ForegroundColor Green
            } else {
                Write-Host "✗ Database tables missing (found $tableCount, expected 7)" -ForegroundColor Red
                $issues += "Run setup_database.ps1 to create tables"
            }
        } else {
            Write-Host "✗ Database 'face_recognition' does not exist" -ForegroundColor Red
            $issues += "Run setup_database.ps1 to create database"
        }
    } else {
        Write-Host "✗ Cannot connect to PostgreSQL" -ForegroundColor Red
        $issues += "Check PostgreSQL password or service status"
    }
    
    $env:PGPASSWORD = $null
} else {
    Write-Host "✗ PostgreSQL not found at expected location" -ForegroundColor Red
    $issues += "Install PostgreSQL 17"
}

# Check ports
Write-Host "Checking ports..." -ForegroundColor Yellow
$ports = @(4200, 3000, 5000, 5432)
foreach ($port in $ports) {
    $portCheck = netstat -ano | Select-String ":$port " | Select-Object -First 1
    if ($portCheck) {
        $processId = ($portCheck -split '\s+')[-1]
        $processName = (Get-Process -Id $processId -ErrorAction SilentlyContinue).ProcessName
        Write-Host "⚠ Port $port is in use by $processName (PID: $processId)" -ForegroundColor Yellow
        $warnings += "Port $port in use - may need to stop existing service"
    } else {
        Write-Host "✓ Port $port is available" -ForegroundColor Green
    }
}

# Check Docker containers
Write-Host "Checking Docker containers..." -ForegroundColor Yellow
try {
    $containers = docker ps --filter "name=face-recognition" --format "{{.Names}}" 2>&1
    if ($LASTEXITCODE -eq 0) {
        if ($containers) {
            Write-Host "✓ Face recognition containers running:" -ForegroundColor Green
            $containers | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
        } else {
            Write-Host "⚠ No face recognition containers running" -ForegroundColor Yellow
            $warnings += "Run 'docker-compose up' to start containers"
        }
    }
} catch {
    Write-Host "⚠ Cannot check Docker containers" -ForegroundColor Yellow
}

# Check unknown_face_images directory
Write-Host "Checking directories..." -ForegroundColor Yellow
$imagesDir = Join-Path (Split-Path -Parent $PSScriptRoot) "unknown_face_images"
if (Test-Path $imagesDir) {
    Write-Host "✓ unknown_face_images directory exists" -ForegroundColor Green
} else {
    Write-Host "✗ unknown_face_images directory missing" -ForegroundColor Red
    $issues += "Create directory: mkdir unknown_face_images"
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Diagnostics Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($issues.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "✓ All checks passed! System is ready for deployment." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. cd .." -ForegroundColor White
    Write-Host "2. docker-compose up --build" -ForegroundColor White
} else {
    if ($issues.Count -gt 0) {
        Write-Host "Critical Issues ($($issues.Count)):" -ForegroundColor Red
        $issues | ForEach-Object { Write-Host "  ✗ $_" -ForegroundColor Red }
        Write-Host ""
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host "Warnings ($($warnings.Count)):" -ForegroundColor Yellow
        $warnings | ForEach-Object { Write-Host "  ⚠ $_" -ForegroundColor Yellow }
        Write-Host ""
    }
    
    Write-Host "Please resolve the issues above before deployment." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "For detailed setup instructions, see:" -ForegroundColor Cyan
Write-Host "  - QUICK_START.md" -ForegroundColor White
Write-Host "  - DEPLOYMENT_GUIDE.md" -ForegroundColor White
Write-Host ""
