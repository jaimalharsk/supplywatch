import random

from ingest.base import BaseIngestor
from signals.models import MaterialSignal


class ComtradeIngestor(BaseIngestor):
    source_name = "comtrade"

    def __init__(self, material: str):
        self.material = material

    async def fetch(self) -> dict:
        return {"trade_hhi": random.uniform(1500, 9000)}

    async def normalize(self, raw: dict) -> MaterialSignal:
        return MaterialSignal(material=self.material, source=self.source_name, trade_hhi=float(raw.get("trade_hhi", 0)))
