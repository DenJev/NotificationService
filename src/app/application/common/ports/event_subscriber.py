from typing import Protocol


class EventConsumer(Protocol):
    """
    Event Subscriber is an interface for consuming domain events
    from an external message broker or queue.

    Implementations can integrate with infrastructure providers
    such as Google Pub/Sub, RabbitMQ, or Kafka, and are responsible
    for deserializing and delivering events to domain-specific
    handlers for asynchronous processing.

    Subscribers typically run in the background and invoke
    a provided callback whenever a new event is available.
    """

    async def _ensure_subscription(self) -> None:
        """ """

    async def subscribe(self) -> None:
        """ """

    async def _ensure_topic(self) -> None:
        """ """
