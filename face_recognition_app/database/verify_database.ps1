# Database Verification Script
# Run this to verify your database is set up correctly

$PSQL_PATH = "C:\Program Files\PostgreSQL\17\bin\psql.exe"
$DB_NAME = "face_recognition"
$DB_USER = "admin"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if psql exists
if (-Not (Test-Path $PSQL_PATH)) {
    Write-Host "✗ PostgreSQL not found at $PSQL_PATH" -ForegroundColor Red
    exit 1
}
Write-Host "✓ PostgreSQL installed" -ForegroundColor Green

# Prompt for password
$DB_PASSWORD = Read-Host "  Enter PostgreSQL password for user 'admin'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($DB_PASSWORD)
$PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
$env:PGPASSWORD = $PlainPassword

# Test connection
Write-Host "Testing connection..." -ForegroundColor Yellow
$testResult = & $PSQL_PATH -U $DB_USER -d postgres -c "SELECT 1" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Cannot connect to PostgreSQL" -ForegroundColor Red
    exit 1
}
Write-Host "✓ PostgreSQL connection successful" -ForegroundColor Green

# Check database exists
Write-Host "Checking database..." -ForegroundColor Yellow
$dbExists = & $PSQL_PATH -U $DB_USER -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>&1
if ($dbExists -ne "1") {
    Write-Host "✗ Database '$DB_NAME' does not exist" -ForegroundColor Red
    Write-Host "Run setup_database.ps1 first" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Database '$DB_NAME' exists" -ForegroundColor Green

# Check pgvector extension
Write-Host "Checking pgvector extension..." -ForegroundColor Yellow
$vectorExists = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT 1 FROM pg_extension WHERE extname='vector'" 2>&1
if ($vectorExists -ne "1") {
    Write-Host "✗ pgvector extension not installed" -ForegroundColor Red
    exit 1
}
$vectorVersion = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT extversion FROM pg_extension WHERE extname='vector'" 2>&1
Write-Host "✓ pgvector extension installed (version $vectorVersion)" -ForegroundColor Green

# Check tables
Write-Host "Checking tables..." -ForegroundColor Yellow
$expectedTables = @("people", "faces", "unknown_faces", "model_versions", "video_sessions", "frames", "detections")
$actualTables = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename" 2>&1

$missingTables = @()
foreach ($table in $expectedTables) {
    if ($actualTables -notcontains $table) {
        $missingTables += $table
    }
}

if ($missingTables.Count -gt 0) {
    Write-Host "✗ Missing tables: $($missingTables -join ', ')" -ForegroundColor Red
    Write-Host "Run setup_database.ps1 to create tables" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ All required tables exist:" -ForegroundColor Green
$actualTables | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }

# Check table row counts
Write-Host ""
Write-Host "Table statistics:" -ForegroundColor Yellow
foreach ($table in $expectedTables) {
    $count = & $PSQL_PATH -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM $table" 2>&1
    Write-Host "  $table : $count rows" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Database verification passed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your database is ready for Docker deployment." -ForegroundColor White
Write-Host ""

$env:PGPASSWORD = $null
