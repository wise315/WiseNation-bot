
from collections.abc import Sequence

from app.events.engine import EventEngine
from app.events.processors.nft_decoder import NFTEventDecoder
from app.schemas.blockchain_activity import EthereumContractLog


class NFTEventProcessor:
    def __init__(
        self,
        decoder: NFTEventDecoder,
        event_engine: EventEngine,
    ):
        self.decoder = decoder
        self.event_engine = event_engine

    async def process_log(
        self,
        log: EthereumContractLog,
    ) -> int:
        events = self.decoder.decode(log)

        for event in events:
            await self.event_engine.publish(event)

        return len(events)

    async def process_logs(
        self,
        logs: Sequence[EthereumContractLog],
    ) -> int:
        count = 0

        for log in logs:
            count += await self.process_log(log)

        return count

