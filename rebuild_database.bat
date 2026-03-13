@echo off
REM ========================================
REM REBUILD VECTOR DATABASE
REM ========================================
echo.
echo ======================================
echo REBUILD VECTOR DATABASE
echo ======================================
echo.

REM Set PYTHONPATH
set PYTHONPATH=%~dp0

REM Run build script
python scripts\build_vector_db.py

echo.
echo ======================================
echo HOAN THANH!
echo ======================================
echo.
echo Ban co the chay chatbot: python run.py
echo.

pause
