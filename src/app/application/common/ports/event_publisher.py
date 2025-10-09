from typing import Protocol


class EventPublisher(Protocol):
    """
    Event Publisher is an interface for sending domain events
    to an external message broker or queue.

    Implementations can integrate with infrastructure providers
    such as Google Pub/Sub, RabbitMQ, or Kafka, and are responsible
    for serializing and dispatching events for asynchronous processing
    by other services.
    """

    async def publish(self) -> None:
        """ """

    async def publish_many(self) -> None:
        """ """

    async def _ensure_topic(self) -> None:
        """ """
