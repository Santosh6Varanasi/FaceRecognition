@echo off
REM === Step 1: Create venv if not exists ===
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM === Step 2: Activate venv ===
call venv\Scripts\activate

REM === Step 3: Run the app ===
echo Starting application...
python app.py