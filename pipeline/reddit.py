"""
Posts SupplyWatch reports to Reddit via PRAW.

Credentials needed in .env:
  REDDIT_CLIENT_ID      — from your Reddit app
  REDDIT_CLIENT_SECRET  — from your Reddit app
  REDDIT_USERNAME       — your Reddit username
  REDDIT_PASSWORD       — your Reddit password

Setup (takes ~2 minutes):
  1. Go to reddit.com/prefs/apps
  2. Click "create another app" at the bottom
  3. Name: SupplyWatch, Type: script, redirect URI: http://localhost:8080
  4. Copy the client ID (under the app name) and client secret
  5. Set the four env vars above

Target subreddits (defined in teaser.py REDDIT_TARGETS):
  r/supplychain, r/manufacturing, r/scarcity, r/commodities

Reddit self-promotion rules:
  - Full content is posted inline (not just a link) — this is fine
  - The waitlist link appears only in the footer, not the title
  - Space posts 10 minutes apart to avoid spam filters
"""

from __future__ import annotations

import os
import time
import logging

import praw
from dotenv import load_dotenv

from .teaser import reddit_title, reddit_body, REDDIT_TARGETS

load_dotenv()

log = logging.getLogger(__name__)

POST_DELAY_SECONDS = 600  # 10 min between subreddit posts to avoid spam filters


class RedditPoster:
    def __init__(self):
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        username = os.getenv("REDDIT_USERNAME")
        password = os.getenv("REDDIT_PASSWORD")

        missing = [k for k, v in {
            "REDDIT_CLIENT_ID": client_id,
            "REDDIT_CLIENT_SECRET": client_secret,
            "REDDIT_USERNAME": username,
            "REDDIT_PASSWORD": password,
        }.items() if not v]
        if missing:
            raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")

        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=f"script:supplywatch:v1.0 (by u/{username})",
        )

    def post(
        self,
        md: str,
        report_date: str,
        substack_url: str = "",
        subreddits: list[str] | None = None,
        delay: int = POST_DELAY_SECONDS,
    ) -> list[dict]:
        """
        Posts the full report to each target subreddit.
        Returns list of {'subreddit', 'post_id', 'url', 'error'} dicts.
        """
        targets = subreddits or REDDIT_TARGETS
        title = reddit_title(md, report_date)
        body = reddit_body(md, report_date, substack_url)

        results = []
        for i, sub in enumerate(targets):
            if i > 0:
                log.info(f"Waiting {delay}s before next post…")
                time.sleep(delay)
            try:
                submission = self.reddit.subreddit(sub).submit(
                    title=title,
                    selftext=body,
                )
                url = f"https://reddit.com{submission.permalink}"
                log.info(f"r/{sub} posted: {url}")
                results.append({"subreddit": sub, "post_id": submission.id, "url": url, "error": None})
            except Exception as e:
                log.error(f"r/{sub} failed: {e}")
                results.append({"subreddit": sub, "post_id": None, "url": None, "error": str(e)})

        return results
