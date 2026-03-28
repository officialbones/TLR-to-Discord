"""Configuration loaded from .env file. No credentials are stored here."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Require an env var to be set. Exit if missing."""
    value = os.getenv(key)
    if not value:
        print(f"ERROR: Required environment variable '{key}' is not set. Check your .env file.", file=sys.stderr)
        sys.exit(1)
    return value


# Database settings — all required from .env
DB_HOST = _require("DB_HOST")
DB_PORT = _require("DB_PORT")
DB_NAME = _require("DB_NAME")
DB_USER = _require("DB_USER")
DB_PASS = _require("DB_PASS")

# Build the connection string from .env fields
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Discord — required
DISCORD_WEBHOOK_URL = _require("DISCORD_WEBHOOK_URL")

# Transcription API — required
TRANSCRIPTION_URL = _require("TRANSCRIPTION_URL")

# Polling — optional with safe defaults
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
STATE_FILE = os.getenv("STATE_FILE", "./state.json")
