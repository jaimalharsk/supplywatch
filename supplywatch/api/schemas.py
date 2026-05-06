from datetime import datetime
from pydantic import BaseModel, Field


class EnvelopeMeta(BaseModel):
    timestamp: datetime
    version: str


class Envelope(BaseModel):
    data: dict | list
    meta: EnvelopeMeta


class AlertSubscribeRequest(BaseModel):
    material_id: int
    threshold: int = Field(ge=0, le=100)
    email: str | None = None
    webhook_url: str | None = None


class CreateApiKeyRequest(BaseModel):
    company_name: str
    tier: str = "free"
