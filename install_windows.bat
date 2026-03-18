@echo off
REM Echo TTS API Server - Windows Installation Script
REM This script installs all Python packages for Windows

echo ==========================================
echo Echo TTS API Server - Windows Installation
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo Python is installed
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

REM Install PyTorch with CUDA support
echo.
echo Installing PyTorch with CUDA support...
pip install torch>=2.9.1 torchaudio>=2.9.1 --index-url https://download.pytorch.org/whl/cu121

REM Install Python dependencies
echo.
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo ==========================================
echo Installation completed successfully!
echo ==========================================
echo.
echo To start the server, run:
echo   venv\Scripts\activate.bat
echo   python -m xtts_api_server
echo.
echo Or use the launcher script:
echo   launcher.bat
echo.
pause
