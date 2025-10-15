from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.pub_sub.entity import Event
from app.infrastructure.sqla_persistence.mappings.event import event_table


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, event: Event):
        await self.add_if_not_exists(event)

    async def add_if_not_exists(self, event: Event):
        stmt = (
            insert(Event)
            .values(
                message_id=event.message_id,
                topic=event.topic,
                event_type=event.event_type,
                status=event.status,
                processing_started_at=event.processing_started_at,
            )
            .on_conflict_do_nothing(
                index_elements=["message_id", "topic"]
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_and_topic(self, message_id: int, topic: str, for_update: bool = False):
        stmt = select(Event).where(event_table.c.message_id == message_id, event_table.c.topic == topic)
        if for_update:
            stmt = stmt.with_for_update()

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self):
        return self.session.select(Event).all()
