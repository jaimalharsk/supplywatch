from abc import ABC, abstractmethod

from signals.models import MaterialSignal


class BaseIngestor(ABC):
    material: str
    source_name: str

    @abstractmethod
    async def fetch(self) -> dict:
        ...

    @abstractmethod
    async def normalize(self, raw: dict) -> MaterialSignal:
        ...

    async def run(self) -> MaterialSignal:
        raw = await self.fetch()
        return await self.normalize(raw)
