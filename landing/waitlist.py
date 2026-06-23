"""
Waitlist email capture — FastAPI router.

Mount in your existing api/ app:
    from landing.waitlist import router as waitlist_router
    app.include_router(waitlist_router)

Or run standalone for testing:
    uvicorn landing.waitlist:app --port 8001

Emails are stored in landing/emails.csv — one line per signup,
with timestamp and source. No DB dependency.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/waitlist")

EMAILS_FILE = Path(__file__).parent / "emails.csv"
EMAIL_RE    = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SubscribeRequest(BaseModel):
    email: str
    source: str = "landing"


def _load_emails() -> set[str]:
    if not EMAILS_FILE.exists():
        return set()
    with open(EMAILS_FILE, newline="") as f:
        return {row["email"].lower() for row in csv.DictReader(f)}


def _append_email(email: str, source: str):
    write_header = not EMAILS_FILE.exists()
    with open(EMAILS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "source", "ts"])
        if write_header:
            writer.writeheader()
        writer.writerow({
            "email":  email.lower(),
            "source": source,
            "ts":     datetime.now(timezone.utc).isoformat(),
        })


@router.post("/subscribe")
def subscribe(req: SubscribeRequest):
    email = req.email.strip().lower()

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Invalid email address.")

    existing = _load_emails()
    if email in existing:
        return {"status": "already_subscribed", "message": "You're already on the list."}

    _append_email(email, req.source)
    return {"status": "subscribed", "message": "You're on the list — brief arrives Monday."}


@router.get("/count")
def count():
    """Returns current waitlist size — useful for social proof."""
    return {"count": len(_load_emails())}


# ── Standalone mode ───────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    app = FastAPI()
    app.include_router(router)
    app.mount("/", StaticFiles(directory=Path(__file__).parent, html=True), name="static")
except ImportError:
    pass
