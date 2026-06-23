"""
Posts SupplyWatch reports to Substack via the unofficial API.

Credentials needed in .env:
  SUBSTACK_EMAIL        — your Substack login email
  SUBSTACK_PASSWORD     — your Substack login password
  SUBSTACK_PUBLICATION  — your publication subdomain, e.g. "supplywatch"
                          (the part before .substack.com)

Setup:
  1. Create a free Substack publication at substack.com
  2. Set the three env vars above
  3. Run scheduler.py — it creates a published post automatically

The unofficial API flow:
  POST /api/v1/login            → get session cookie (substack.sid)
  POST /api/v1/drafts           → create draft, get post ID
  POST /api/v1/posts/{id}/publish → publish immediately
"""

from __future__ import annotations

import os
import requests
from dotenv import load_dotenv

from .teaser import substack_title, substack_subtitle, substack_body_html

load_dotenv()

BASE = "https://substack.com"


class SubstackPoster:
    def __init__(self):
        self.email = os.getenv("SUBSTACK_EMAIL")
        self.password = os.getenv("SUBSTACK_PASSWORD")
        self.publication = os.getenv("SUBSTACK_PUBLICATION")

        missing = [k for k, v in {
            "SUBSTACK_EMAIL": self.email,
            "SUBSTACK_PASSWORD": self.password,
            "SUBSTACK_PUBLICATION": self.publication,
        }.items() if not v]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

        self._pub_base = f"https://{self.publication}.substack.com"
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "SupplyWatch/1.0"})

    def _login(self):
        resp = self._session.post(
            f"{BASE}/api/v1/login",
            json={"email": self.email, "password": self.password, "captcha_response": ""},
        )
        resp.raise_for_status()

    def _create_draft(self, title: str, subtitle: str, body_html: str) -> str:
        """Creates a draft and returns its post ID."""
        resp = self._session.post(
            f"{self._pub_base}/api/v1/drafts",
            json={
                "draft_title": title,
                "draft_subtitle": subtitle,
                "draft_body": body_html,
                "type": "newsletter",
                "section_chosen": False,
            },
        )
        resp.raise_for_status()
        return str(resp.json()["id"])

    def _publish(self, post_id: str):
        resp = self._session.post(
            f"{self._pub_base}/api/v1/posts/{post_id}/publish",
            json={"send": True, "share_automatically": False},
        )
        resp.raise_for_status()

    def post(self, md: str, report_date: str, publish: bool = True) -> dict:
        """
        Converts the markdown report and posts to Substack.
        Returns {'post_id': ..., 'url': ..., 'published': bool}
        """
        title = substack_title(md, report_date)
        subtitle = substack_subtitle(md)
        body_html = substack_body_html(md, report_date)

        self._login()
        post_id = self._create_draft(title, subtitle, body_html)

        if publish:
            self._publish(post_id)

        url = f"{self._pub_base}/p/{post_id}"
        return {"post_id": post_id, "url": url, "published": publish}
