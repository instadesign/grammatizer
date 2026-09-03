"""Environment configuration. In local dev, python-dotenv loads backend/.env.
In production, systemd's EnvironmentFile= supplies real env vars — no .env file on the server."""

import os

from dotenv import load_dotenv

load_dotenv()

# "null" is what a browser sends as the Origin header for a page opened straight from
# disk (file://) rather than through serve.py -- confirmed live: opening index.html
# directly (no dev server) got every /api/generate/beat call rejected at the CORS
# preflight ("Disallowed CORS origin", a 400 before the request ever reached a route),
# which surfaced to the reader as the generic "machine isn't answering" network error
# -- indistinguishable from a real connectivity problem. js/api.js already expects and
# handles the file:// case (it points straight at 127.0.0.1:8000 instead of a relative
# path), so the backend's allowlist needs to match that, for local dev only -- this
# constant is entirely replaced by the ALLOWED_ORIGINS env var in production, where
# everything is same-origin behind Nginx anyway and this never applies.
DEFAULT_DEV_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500,null"

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS).split(",")
    if origin.strip()
]
