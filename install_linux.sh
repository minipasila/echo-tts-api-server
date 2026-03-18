#!/bin/bash

# Echo TTS API Server - Linux Installation Script
# This script installs all system dependencies and Python packages for Linux

set -e  # Exit on error

echo "=========================================="
echo "Echo TTS API Server - Linux Installation"
echo "=========================================="
echo ""

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    VERSION=$VERSION_ID
else
    echo "Error: Cannot detect Linux distribution"
    exit 1
fi

echo "Detected distribution: $DISTRO $VERSION"
echo ""

# Install system dependencies based on distribution
case $DISTRO in
    ubuntu|debian)
        echo "Installing system dependencies for Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y \
            python3-dev \
            python3-venv \
            portaudio19-dev \
            libportaudio2 \
            libasound2-dev \
            libportaudiocpp0 \
            ffmpeg \
            git
        ;;
    
    fedora|rhel|centos)
        echo "Installing system dependencies for Fedora/RHEL/CentOS..."
        sudo dnf install -y \
            python3-devel \
            python3-venv \
            portaudio-devel \
            alsa-lib-devel \
            ffmpeg \
            git
        ;;
    
    arch|manjaro)
        echo "Installing system dependencies for Arch Linux..."
        sudo pacman -S --noconfirm \
            python \
            portaudio \
            alsa-lib \
            ffmpeg \
            git
        ;;
    
    *)
        echo "Warning: Unsupported distribution: $DISTRO"
        echo "Please install the following manually:"
        echo "  - python3-dev / python3-devel"
        echo "  - portaudio19-dev / portaudio-devel"
        echo "  - libasound2-dev / alsa-lib-devel"
        echo "  - ffmpeg"
        echo "  - git"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
esac

echo ""
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

# Install PyTorch with CUDA support
echo ""
echo "Installing PyTorch with CUDA support..."
pip install torch>=2.9.1 torchaudio>=2.9.1 --index-url https://download.pytorch.org/whl/cu121

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
echo "Or use the launcher script:"
echo "  ./launcher.sh"
echo ""
