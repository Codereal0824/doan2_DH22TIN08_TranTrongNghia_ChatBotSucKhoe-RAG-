@echo off
REM Batch script khởi động chatbot trên Windows
REM Sử dụng: Double-click file này hoặc chạy "start_chatbot.bat" trong CMD

echo ======================================================================
echo    CHATBOT TU VAN SUC KHOE AI
echo ======================================================================
echo.

REM Kiểm tra virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found. Using global Python.
)

REM Chạy ứng dụng
echo [INFO] Starting chatbot server...
echo.
python run.py

pause
