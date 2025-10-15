from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.infrastructure.adapters.database.repositories.event_repository import EventRepository


@runtime_checkable
class UnitOfWork(Protocol):
    events: EventRepository
    session: AsyncSession

    async def __aenter__(self) -> "UnitOfWork": ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
