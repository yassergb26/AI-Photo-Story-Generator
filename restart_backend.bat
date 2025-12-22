@echo off
echo ============================================
echo Restarting Backend with Unified Pattern Detection
echo ============================================
echo.

echo Step 1: Stopping all Python processes...
taskkill /F /IM python.exe 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Python processes stopped
) else (
    echo ℹ No Python processes were running
)
echo.

echo Step 2: Waiting 2 seconds...
timeout /t 2 /nobreak >nul
echo.

echo Step 3: Starting backend server...
cd backend
..\venv\Scripts\python.exe main.py
