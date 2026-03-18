#!/bin/bash

# Echo TTS API Server - macOS Installation Script
# This script installs all system dependencies and Python packages for macOS

set -e  # Exit on error

echo "=========================================="
echo "Echo TTS API Server - macOS Installation"
echo "=========================================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is not installed"
    echo "Please install Homebrew first:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✓ Homebrew is installed"
echo ""

# Install system dependencies using Homebrew
echo "Installing system dependencies..."
brew install portaudio ffmpeg git

echo "✓ System dependencies installed"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA support (macOS uses MPS, not CUDA)
echo ""
echo "Installing PyTorch..."
pip install torch>=2.9.1 torchaudio>=2.9.1

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✓ Installation completed successfully!"
echo "=========================================="
echo ""
echo "To start the server, run:"
echo "  source venv/bin/activate"
echo "  python -m xtts_api_server"
echo ""
echo "Note: On macOS, PyTorch will use MPS (Metal Performance Shaders) for GPU acceleration."
echo "      CUDA is not supported on macOS."
echo ""
