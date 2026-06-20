@echo off
echo ============================================
echo   VendorSentry Frontend Setup
echo ============================================
echo.

cd /d "%~dp0app"

REM Check if node_modules exists
if not exist "node_modules" (
    echo [1/2] Installing npm dependencies...
    npm install
) else (
    echo [1/2] Dependencies already installed.
)

echo [2/2] Starting Vite dev server...
echo.
echo ============================================
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo ============================================
echo.

npm run dev
