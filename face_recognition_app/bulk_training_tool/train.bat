@echo off
REM Bulk Training Tool - Windows Batch Script
REM Usage: train.bat

echo ================================================================================
echo   Bulk Training Tool
echo ================================================================================
echo.

REM Check if training_data exists
if not exist "..\..\training_data\training_data" (
    echo ERROR: training_data folder not found!
    echo Please create: training_data\training_data\
    echo.
    echo Expected structure:
    echo   training_data\
    echo   └── training_data\
    echo       ├── person1\
    echo       │   ├── image1.jpg
    echo       │   └── image2.jpg
    echo       └── person2\
    echo           └── image1.jpg
    echo.
    pause
    exit /b 1
)

REM Run training
python bulk_train.py --training-data-dir ..\..\training_data\training_data

echo.
pause
