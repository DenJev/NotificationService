from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.application.common.ports.unit_of_work import UnitOfWork
from app.infrastructure.adapters.database.repositories.event_repository import EventRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session = session

    async def __aenter__(self):
        self.events = EventRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            await self.session.rollback()
        else:
            await self.session.commit()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
