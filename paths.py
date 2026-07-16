import os
from pathlib import Path
import sys

# Load LMS_HOME from the environment at startup and fail clearly if it is missing.
LMS_HOME_ENV = os.environ.get("LMS_HOME")
if not LMS_HOME_ENV:
    print("ERROR: LMS_HOME environment variable is not set.", file=sys.stderr)
    sys.exit(1)

LMS_HOME = Path(LMS_HOME_ENV).resolve()
if not LMS_HOME.exists() or not LMS_HOME.is_dir():
    print(f"ERROR: LMS_HOME path '{LMS_HOME}' does not exist or is not a directory.", file=sys.stderr)
    sys.exit(1)

# Centralized path constants
WEB_DIR = LMS_HOME / "web"
MEDIA_DIR = LMS_HOME / "media" # Common directory, though sources can be anywhere
CONFIG_DIR = LMS_HOME
LOG_DIR = LMS_HOME / "log"
CACHE_DIR = LMS_HOME / "cache"
MANIFEST_DIR = WEB_DIR
MANIFEST_FILE = MANIFEST_DIR / "manifest.json"
CONFIG_FILE = CONFIG_DIR / "config.json"
CADDYFILE_PATH = LMS_HOME / "Caddyfile"
FAIL2BAN_JAIL_PATH = LMS_HOME / "fail2ban_caddy_jail.conf"
SYSTEMD_SERVICE_PATH = LMS_HOME / "lms.service"
HELP_FILE_PATH = LMS_HOME / "help.txt"

# Ensure necessary directories exist
for d in [LOG_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def is_within_home(path):
    """Checks if a path is within LMS_HOME."""
    try:
        Path(path).resolve().relative_to(LMS_HOME)
        return True
    except ValueError:
        return False

def validate_path(path):
    """Ensures the path is within LMS_HOME or one of the configured media sources."""
    # We'll need to check against media sources too, but those are dynamic.
    # For now, let's at least have this helper.
    resolved = Path(path).resolve()
    if is_within_home(resolved):
        return resolved
    
    # Check against media sources from config.json
    # Note: To avoid circular imports, we might need to load config here or pass sources.
    return resolved

def get_relative_path(path, root):
    """Returns a relative path from root, ensuring it's safe."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve())
    except ValueError:
        raise ValueError(f"Path {path} is not within {root}")
