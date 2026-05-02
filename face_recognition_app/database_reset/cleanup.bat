@echo off
REM Complete System Cleanup Script
REM WARNING: This will DELETE ALL DATA!

echo ================================================================================
echo   COMPLETE SYSTEM CLEANUP
echo ================================================================================
echo.
echo WARNING: This will DELETE ALL DATA including:
echo   - All database tables and data
echo   - All uploaded videos
echo   - All annotated videos  
echo   - All unknown face images
echo   - All training images
echo   - All model versions
echo.
echo This action CANNOT be undone!
echo ================================================================================
echo.

python cleanup_all.py

echo.
pause
