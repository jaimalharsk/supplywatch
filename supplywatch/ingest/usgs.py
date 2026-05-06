import random

from ingest.base import BaseIngestor
from signals.models import MaterialSignal


class USGSIngestor(BaseIngestor):
    source_name = "usgs"

    def __init__(self, material: str):
        self.material = material

    async def fetch(self) -> dict:
        return {"price_delta": random.uniform(0, 60)}

    async def normalize(self, raw: dict) -> MaterialSignal:
        return MaterialSignal(material=self.material, source=self.source_name, price_delta=float(raw.get("price_delta", 0)))
