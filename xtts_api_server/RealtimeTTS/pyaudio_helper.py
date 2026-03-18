"""
PyAudio helper module with graceful import handling.

This module provides a safe way to import PyAudio with helpful error messages
when the library is not installed or cannot be imported.
"""

import logging
import sys

# Try to import PyAudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    PYAUDIO_VERSION = pyaudio.__version__
except ImportError as e:
    PYAUDIO_AVAILABLE = False
    PYAUDIO_VERSION = None
    pyaudio = None
    
    # Provide helpful error message
    error_msg = """
================================================================================
PyAudio Import Error
================================================================================

PyAudio is required for streaming audio features but is not installed.

To fix this issue, follow the platform-specific instructions below:

Linux (Ubuntu/Debian):
  sudo apt-get install -y python3-dev portaudio19-dev libportaudio2 libasound2-dev
  pip install PyAudio==0.2.14

Linux (Fedora/RHEL/CentOS):
  sudo dnf install -y python3-devel portaudio-devel alsa-lib-devel
  pip install PyAudio==0.2.14

Linux (Arch Linux):
  sudo pacman -S portaudio python
  pip install PyAudio==0.2.14

macOS:
  brew install portaudio
  pip install PyAudio==0.2.14

Windows:
  pip install PyAudio==0.2.14

Alternative: Force pre-built wheels
  pip install --only-binary :all: PyAudio==0.2.14

For more information, see:
  https://github.com/minipasila/echo-tts-api-server#troubleshooting

Note: Streaming features will be disabled without PyAudio.
================================================================================
"""
    logging.error(error_msg)
    print(error_msg, file=sys.stderr)


def check_pyaudio():
    """
    Check if PyAudio is available and return status.
    
    Returns:
        tuple: (is_available: bool, version: str or None, error_message: str or None)
    """
    if PYAUDIO_AVAILABLE:
        return True, PYAUDIO_VERSION, None
    else:
        return False, None, "PyAudio is not installed. Streaming features will be disabled."


def require_pyaudio(feature_name="streaming"):
    """
    Decorator to require PyAudio for a function.
    
    Args:
        feature_name (str): Name of the feature that requires PyAudio
        
    Returns:
        decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not PYAUDIO_AVAILABLE:
                error_msg = f"Cannot use {feature_name}: PyAudio is not installed."
                logging.error(error_msg)
                raise ImportError(error_msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_pyaudio_constants():
    """
    Get PyAudio constants if available, or provide fallback values.
    
    Returns:
        dict: Dictionary of PyAudio constants or None if not available
    """
    if not PYAUDIO_AVAILABLE:
        return None
    
    return {
        'paInt16': pyaudio.paInt16,
        'paFloat32': pyaudio.paFloat32,
        'paCustomFormat': pyaudio.paCustomFormat,
    }


# Export for backward compatibility
__all__ = [
    'pyaudio',
    'PYAUDIO_AVAILABLE',
    'PYAUDIO_VERSION',
    'check_pyaudio',
    'require_pyaudio',
    'get_pyaudio_constants',
]
