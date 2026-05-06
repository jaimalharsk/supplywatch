from signals.models import MaterialSignal
from signals.scorer import disruption_score


def test_disruption_score_range():
    signals = [
        MaterialSignal(material='Lithium', source='usgs', price_delta=20),
        MaterialSignal(material='Lithium', source='sanctions', export_mentions=2),
        MaterialSignal(material='Lithium', source='comtrade', trade_hhi=5000),
    ]
    score, factors = disruption_score(signals)
    assert 0 <= score <= 100
    assert set(factors.keys()) == {'price', 'export', 'trade'}
