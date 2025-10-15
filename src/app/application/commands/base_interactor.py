import hashlib
from datetime import datetime, timezone

from sqlalchemy import text

from app.application.common.exceptions.event import EventProcessedError, EventProcessingError
from app.application.common.ports.unit_of_work import UnitOfWork
from app.domain.entities.pub_sub.entity import Event, PubSubMessage
from app.domain.entities.pub_sub.value_objects import EventStatus


class BaseEventInteractor:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    async def process_event(self, message: PubSubMessage):
        """Override this in a subclass"""
        raise NotImplementedError

    async def lock_db(self, uow: UnitOfWork, topic: str, message_id: str):
        topic_hash = int(hashlib.md5(topic.encode()).hexdigest(), 16) % (2**31)
        message_hash = int(hashlib.md5(message_id.encode()).hexdigest(), 16) % (2**31)

        lock_result = await uow.session.execute(
            text("SELECT pg_try_advisory_xact_lock(:topic_key, :message_key)"),
            {"topic_key": topic_hash, "message_key": message_hash},
        )
        if not lock_result.scalar():
            raise EventProcessingError(f"Message {message_id} is already being processed")

    async def __call__(self, message: PubSubMessage):
        message_id = message.message.message_id
        topic = message.topic

        async with self.unit_of_work as uow:
            try:
                await self.lock_db(uow, topic, message_id)
            except EventProcessingError:
                raise

            event = await uow.events.get_by_id_and_topic(message_id, topic, for_update=True)

            if not event:
                event = Event(
                    message_id=message_id,
                    topic=topic,
                    event_type=message.event_type,
                    status=EventStatus.PROCESSING,
                    processing_started_at=datetime.now(timezone.utc),
                )
                await uow.events.add(event)
            elif event.status == EventStatus.PROCESSED:
                raise EventProcessedError("Already processed")
            elif event.status == EventStatus.PROCESSING:
                raise EventProcessingError("Already being processed")
            elif event.status == EventStatus.FAILED:
                event.change_status(EventStatus.PROCESSING)

        try:
            await self.process_event(message)
            final_status = EventStatus.PROCESSED
        except Exception:
            final_status = EventStatus.FAILED
            raise
        finally:
            async with self.unit_of_work as uow:
                event = await uow.events.get_by_id_and_topic(message_id, topic, for_update=True)
                if event:
                    event.change_status(final_status)
