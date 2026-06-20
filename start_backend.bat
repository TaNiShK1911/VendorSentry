@echo off
echo ============================================
echo   VendorSentry Backend Setup
echo ============================================
echo.

cd /d "%~dp0backend"

REM Check if venv exists
if not exist "venv" (
    echo [1/4] Creating Python virtual environment...
    python -m venv venv
) else (
    echo [1/4] Virtual environment already exists.
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install -r requirements.txt --quiet

echo [4/4] Initializing database and seeding data...
python scripts\init_db.py

echo.
echo ============================================
echo   Starting VendorSentry API Server
echo   http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo ============================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
