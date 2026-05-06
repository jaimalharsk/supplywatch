import asyncio

from ingest.comtrade import ComtradeIngestor
from ingest.sanctions import SanctionsIngestor
from ingest.usgs import USGSIngestor


def test_ingestors_return_signal():
    async def _run():
        for cls in (USGSIngestor, ComtradeIngestor, SanctionsIngestor):
            ingestor = cls('Cobalt')
            signal = await ingestor.run()
            assert signal.material == 'Cobalt'
            assert signal.source
    asyncio.run(_run())
