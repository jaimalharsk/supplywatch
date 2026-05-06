from signals.models import MaterialSignal

PRICE_WEIGHT = 0.30
EXPORT_WEIGHT = 0.40
TRADE_WEIGHT = 0.30


def disruption_score(signals: list[MaterialSignal]) -> tuple[int, dict]:
    """Pure scoring function with no side effects.

    Weighted factors:
    - price delta: 30%
    - export restriction mentions: 40%
    - trade concentration (HHI): 30%
    """
    if not signals:
        return 0, {"price": 0, "export": 0, "trade": 0}

    price = min(100, max(0, int(sum(max(0, s.price_delta) for s in signals) / len(signals))))
    export = min(100, max(0, int(sum(min(100, s.export_mentions * 20) for s in signals) / len(signals))))
    trade = min(100, max(0, int(sum(min(100, s.trade_hhi / 100) for s in signals) / len(signals))))

    score = int(price * PRICE_WEIGHT + export * EXPORT_WEIGHT + trade * TRADE_WEIGHT)
    return score, {"price": price, "export": export, "trade": trade}


class DisruptionScorer:
    @staticmethod
    def score(signals: list[MaterialSignal]) -> tuple[int, dict]:
        return disruption_score(signals)
