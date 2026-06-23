"""
Email fallback for SupplyWatch — sends the bite-sized brief to Gmail via SMTP.

Requires in .env:
    GMAIL_USER=you@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # from myaccount.google.com/apppasswords

Usage:
    from pipeline.email_sender import EmailSender
    EmailSender().send(markdown_text, report_date)
"""

from __future__ import annotations

import logging
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from pipeline.teaser import substack_body_html, email_subject

load_dotenv()
log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class EmailSender:
    def __init__(self):
        self.user = os.getenv("GMAIL_USER") or os.getenv("SUBSTACK_EMAIL")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        if not self.password:
            raise EnvironmentError(
                "GMAIL_APP_PASSWORD not set — generate one at "
                "myaccount.google.com → Security → App passwords"
            )

    def send(self, md: str, report_date: str, to: str) -> None:
        subject = email_subject(md, report_date)
        html_body = _wrap_email(substack_body_html(md, report_date), report_date)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SupplyWatch <{self.user}>"
        msg["To"] = to
        msg.attach(MIMEText(_html_to_plain(html_body), "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(self.user, self.password.replace(" ", ""))
            smtp.sendmail(self.user, to, msg.as_string())

        log.info(f"Email sent to {to}: {subject}")

    def prompt_and_send(self, md: str, report_date: str) -> None:
        """Ask for a destination email interactively, then send."""
        print("\n" + "─" * 50)
        print("  SupplyWatch — send brief to email")
        print("─" * 50)
        while True:
            email = input("  Enter email address: ").strip()
            if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                break
            print("  Invalid address, try again.")
        print(f"  Sending to {email}…")
        self.send(md, report_date, to=email)
        print(f"  ✓ Sent! Check {email}\n")


def _wrap_email(body_html: str, report_date: str) -> str:
    return f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 600px; margin: 0 auto; padding: 24px; color: #1a1a1a; line-height: 1.6; }}
  strong {{ color: #111; }}
  a {{ color: #d62828; }}
  ul {{ padding-left: 1.4em; }}
  li {{ margin-bottom: 6px; }}
  hr {{ border: none; border-top: 1px solid #eee; margin: 24px 0; }}
  .header {{ border-left: 4px solid #d62828; padding-left: 12px; margin-bottom: 20px; }}
  .header h1 {{ font-size: 1.1rem; margin: 0; }}
  .header p {{ font-size: 0.8rem; color: #666; margin: 4px 0 0; }}
</style>
</head>
<body>
<div class="header">
  <h1>SupplyWatch</h1>
  <p>Weekly Disruption Brief — {report_date}</p>
</div>
{body_html}
</body>
</html>"""


def _html_to_plain(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<li>", "• ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
