import random

from ingest.base import BaseIngestor
from signals.models import MaterialSignal


class SanctionsIngestor(BaseIngestor):
    source_name = "sanctions"

    def __init__(self, material: str):
        self.material = material

    async def fetch(self) -> dict:
        return {"mentions": random.randint(0, 5)}

    async def normalize(self, raw: dict) -> MaterialSignal:
        return MaterialSignal(material=self.material, source=self.source_name, export_mentions=int(raw.get("mentions", 0)))
