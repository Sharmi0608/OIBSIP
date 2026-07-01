from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.resolve()

# Networking
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9009
BUFFER_SIZE = 4096
ENCODING = "utf-8"

# Files and folders
HISTORY_DIR = BASE_DIR / "history"
RECEIVED_DIR = BASE_DIR / "received_files"
SENT_DIR = BASE_DIR / "sent_files"
ASSETS_DIR = BASE_DIR / "assets"
DB_PATH = BASE_DIR / "users.db"

for p in (HISTORY_DIR, RECEIVED_DIR, SENT_DIR, ASSETS_DIR):
    os.makedirs(p, exist_ok=True)

# Cryptography
# NOTE: In production, store keys securely. For this internship project we keep a single Fernet key.
FERNET_KEY_FILE = BASE_DIR / "fernet.key"

def load_or_create_key():
    from cryptography.fernet import Fernet
    if FERNET_KEY_FILE.exists():
        return FERNET_KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    FERNET_KEY_FILE.write_bytes(key)
    return key

FERNET_KEY = load_or_create_key()

# UI Theme
THEME = {
    "bg": "#23272A",
    "panel": "#2C2F33",
    "card": "#40444B",
    "accent": "#7289DA",
    "success": "#57F287",
    "text": "#FFFFFF",
    "muted": "#B9BBBE"
}

# Allowed file extensions
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
VIDEO_EXT = {".mp4", ".avi", ".mov"}
DOC_EXT = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".zip"}
ALLOWED_EXT = IMAGE_EXT | VIDEO_EXT | DOC_EXT

# Chat rooms
DEFAULT_ROOM = "General"
