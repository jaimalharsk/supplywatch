import httpx
import resend

from core.config import get_settings


class AlertDispatcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        resend.api_key = self.settings.resend_api_key

    async def send_email(self, to: str, subject: str, body: str):
        if not self.settings.resend_api_key:
            print(f"[warn] resend key missing; skipping email to {to}")
            return
        resend.Emails.send({"from": self.settings.resend_from_email, "to": [to], "subject": subject, "text": body})

    async def send_webhook(self, url: str, payload: dict):
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)

    async def dispatch(self, subscription, score: int):
        message = f"SupplyWatch alert: material_id={subscription.material_id} crossed threshold={subscription.threshold} with score={score}"
        if subscription.email:
            await self.send_email(subscription.email, "Supply disruption alert", message)
        if subscription.webhook_url:
            await self.send_webhook(subscription.webhook_url, {"message": message, "score": score})
        return message
