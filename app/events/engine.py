
import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from app.events.schemas import BlockchainEvent, EventType


logger = logging.getLogger(__name__)

EventHandler = Callable[[BlockchainEvent], Awaitable[None]]


class EventEngine:
    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = (
            defaultdict(list)
        )

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        if not callable(handler):
            raise TypeError("Event handler must be callable.")

        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        handlers = self._handlers.get(event_type)

        if handlers and handler in handlers:
            handlers.remove(handler)

    async def publish(
        self,
        event: BlockchainEvent,
        *,
        raise_on_error: bool = False,
    ) -> None:
        if not isinstance(event, BlockchainEvent):
            raise TypeError("Expected a BlockchainEvent instance.")

        handlers = tuple(
            self._handlers.get(event.event_type, [])
        )

        if not handlers:
            logger.debug(
                "No handlers registered for %s",
                event.event_type.value,
            )
            return

        results = await asyncio.gather(
            *(handler(event) for handler in handlers),
            return_exceptions=True,
        )

        failures: list[BaseException] = []

        for result in results:
            if isinstance(result, BaseException):
                failures.append(result)

                logger.error(
                    "Event handler failed for event %s",
                    event.event_id,
                    exc_info=(
                        type(result),
                        result,
                        result.__traceback__,
                    ),
                )

        if raise_on_error and failures:
            raise ExceptionGroup(
                "One or more event handlers failed.",
                failures,
            )

    def subscriber_count(
        self,
        event_type: EventType,
    ) -> int:
        return len(self._handlers.get(event_type, []))
