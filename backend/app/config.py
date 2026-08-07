"""Environment configuration. In local dev, python-dotenv loads backend/.env.
In production, systemd's EnvironmentFile= supplies real env vars — no .env file on the server."""

import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DEV_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS).split(",")
    if origin.strip()
]
