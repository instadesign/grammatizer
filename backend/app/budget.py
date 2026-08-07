"""Daily usage budget for the Claude "backup" engine only. Gemini/Groq are BYOK —
each visitor spends their own quota, so no cap is needed there. Claude backup uses
the *operator's* own key shared across every visitor, so it needs a hard, shared
daily cap or one enthusiastic visitor could run up a real bill.

SQLite (stdlib, no new dependency) rather than a plain in-memory counter: the
systemd unit runs multiple uvicorn workers, and an in-memory counter wouldn't be
shared across them (each worker would silently allow its own capful). SQLite's
file locking gives correct shared accounting across processes and survives restarts.
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(os.environ.get("CLAUDE_BUDGET_DB", str(Path(__file__).parent / "claude_budget.sqlite3")))
DAILY_REQUEST_CAP = int(os.environ.get("CLAUDE_DAILY_REQUEST_CAP", "200"))
DAILY_TOKEN_CAP = int(os.environ.get("CLAUDE_DAILY_TOKEN_CAP", "40000"))  # ~$0.20/day worst case at Haiku 4.5 output pricing


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS claude_usage ("
        "day TEXT PRIMARY KEY, requests INTEGER NOT NULL, output_tokens INTEGER NOT NULL)"
    )
    return conn


def check_and_reserve() -> bool:
    """Call before making a Claude call. Reserves one request slot and returns True
    if under budget; returns False (reserving nothing) if today's cap is already hit."""
    today = date.today().isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT requests, output_tokens FROM claude_usage WHERE day = ?", (today,)
        ).fetchone()
        requests, tokens = row if row else (0, 0)
        if requests >= DAILY_REQUEST_CAP or tokens >= DAILY_TOKEN_CAP:
            return False
        if row:
            conn.execute("UPDATE claude_usage SET requests = requests + 1 WHERE day = ?", (today,))
        else:
            conn.execute(
                "INSERT INTO claude_usage (day, requests, output_tokens) VALUES (?, 1, 0)", (today,)
            )
        conn.commit()
    return True


def record_usage(output_tokens: int) -> None:
    """Call after a successful Claude call with the real token count from the
    response, so the token cap reflects actual spend, not just the request count."""
    today = date.today().isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE claude_usage SET output_tokens = output_tokens + ? WHERE day = ?",
            (max(output_tokens, 0), today),
        )
        conn.commit()
