# PostgreSQL Database Setup Script for Windows
# Run this script in PowerShell as Administrator

$PSQL_PATH = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
$DB_NAME = "face_recognition"
$DB_USER = "admin"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Face Recognition Database Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if psql exists
if (-Not (Test-Path $PSQL_PATH)) {
    Write-Host "ERROR: PostgreSQL not found at $PSQL_PATH" -ForegroundColor Red
    Write-Host "Please install PostgreSQL 17 first." -ForegroundColor Red
    exit 1
}

Write-Host "✓ PostgreSQL found" -ForegroundColor Green

# Prompt for password
$DB_PASSWORD = Read-Host "Enter PostgreSQL password for user 'admin'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD)
$PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Set environment variable for password
$env:PGPASSWORD = $PlainPassword

Write-Host ""
Write-Host "Step 1: Testing PostgreSQL connection..." -ForegroundColor Yellow

# Test connection
$testResult = & $PSQL_PATH -U $DB_USER -d postgres -c "SELECT 1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot connect to PostgreSQL" -ForegroundColor Red
    Write-Host $testResult -ForegroundColor Red
    exit 1
}

Write-Host "✓ PostgreSQL connection successful" -ForegroundColor Green

Write-Host ""
Write-Host "Step 2: Checking if database exists..." -ForegroundColor Yellow

# Check if database exists
$dbExists = & $PSQL_PATH -U $DB_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>&1

if ($dbExists -eq "1") {
    Write-Host "⚠ Database '$DB_NAME' already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to drop and recreate it? (yes/no)"
    if ($response -eq "yes") {
        Write-Host "Dropping existing database..." -ForegroundColor Yellow
        & $PSQL_PATH -U $DB_USER -d postgres -c "DROP DATABASE $DB_NAME" 2>&1
        Write-Host "✓ Database dropped" -ForegroundColor Green
    } else {
        Write-Host "Skipping database creation" -ForegroundColor Yellow
        $skipCreate = $true
    }
}

if (-Not $skipCreate) {
    Write-Host "Creating database '$DB_NAME'..." -ForegroundColor Yellow
    & $PSQL_PATH -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create database" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Database created" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 3: Installing pgvector extension..." -ForegroundColor Yellow

# Check if pgvector is available
$vectorCheck = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT 1 FROM pg_available_extensions WHERE name='vector'" 2>&1

if ($vectorCheck -ne "1") {
    Write-Host "ERROR: pgvector extension is not available" -ForegroundColor Red
    Write-Host "Please install pgvector for PostgreSQL 17:" -ForegroundColor Red
    Write-Host "Download from: https://github.com/pgvector/pgvector/releases" -ForegroundColor Yellow
    exit 1
}

# Enable pgvector extension
& $PSQL_PATH -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create vector extension" -ForegroundColor Red
    exit 1
}

Write-Host "✓ pgvector extension installed" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Running schema migrations..." -ForegroundColor Yellow

# Get script directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Run migration files in order
$migrations = @(
    "01-init-pgvector.sql",
    "02-create-tables.sql",
    "03-create-indexes.sql"
)

foreach ($migration in $migrations) {
    $migrationPath = Join-Path $SCRIPT_DIR $migration
    
    if (-Not (Test-Path $migrationPath)) {
        Write-Host "ERROR: Migration file not found: $migration" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  Running $migration..." -ForegroundColor Cyan
    & $PSQL_PATH -U $DB_USER -d $DB_NAME -f $migrationPath 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to run $migration" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "  ✓ $migration completed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 5: Verifying database setup..." -ForegroundColor Yellow

# Check tables
$tables = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename" 2>&1

Write-Host "Tables created:" -ForegroundColor Cyan
$tables | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }

# Check vector extension
$vectorVersion = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT extversion FROM pg_extension WHERE extname='vector'" 2>&1
Write-Host "pgvector version: $vectorVersion" -ForegroundColor Cyan

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Database setup completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Database connection string:" -ForegroundColor Yellow
Write-Host "postgresql://$DB_USER:admin@localhost:5432/$DB_NAME" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update docker-compose.yml with your PostgreSQL password" -ForegroundColor White
Write-Host "2. Run: docker-compose up --build" -ForegroundColor White
Write-Host ""

# Clear password from environment
$env:PGPASSWORD = $null
