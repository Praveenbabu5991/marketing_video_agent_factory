"""
Configuration settings for Marketing Video Agent Factory.
All settings are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# API Configuration
# =============================================================================
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-3-pro-image-preview")
VIDEO_MODEL = os.getenv("VIDEO_MODEL", "veo-3.1-generate-preview")

# =============================================================================
# Server Configuration
# =============================================================================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5002))  # Different port from hylancer (5001)
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Allowed origins for CORS (comma-separated in env)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5002,http://127.0.0.1:5002").split(",")

# =============================================================================
# Path Configuration
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
GENERATED_DIR = Path(os.getenv("GENERATED_DIR", str(BASE_DIR / "generated")))
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "marketing_video_agent.db")))

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# =============================================================================
# File Upload Limits
# =============================================================================
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 10))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", 4096))

# =============================================================================
# Rate Limiting
# =============================================================================
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 60))  # requests per minute
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # window in seconds

# =============================================================================
# Session Configuration
# =============================================================================
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", 24))
MAX_SESSIONS_PER_USER = int(os.getenv("MAX_SESSIONS_PER_USER", 10))

# =============================================================================
# Agent Configuration
# =============================================================================
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY_SECONDS = float(os.getenv("RETRY_DELAY_SECONDS", 1.0))
