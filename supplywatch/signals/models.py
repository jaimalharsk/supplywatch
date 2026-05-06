from dataclasses import dataclass, field


@dataclass
class MaterialSignal:
    material: str
    source: str
    price_delta: float = 0.0
    export_mentions: int = 0
    trade_hhi: float = 0.0
    metadata: dict = field(default_factory=dict)
