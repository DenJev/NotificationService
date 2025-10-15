# pylint: disable=C0301 (line-too-long)
import logging
from typing import AsyncIterable, cast

from dishka import Provider, Scope, provide, provide_all
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.application.commands.game_digest import GameDigestInteractor
from app.application.common.ports.unit_of_work import UnitOfWork
from app.infrastructure.adapters.database.repositories.event_repository import EventRepository
from app.infrastructure.adapters.database.sqlalc_unit_of_work import SqlAlchemyUnitOfWork
from app.setup.config.settings import PostgresDsn, SqlaEngineSettings

log = logging.getLogger(__name__)


class CommonInfrastructureProvider(Provider):
    scope = Scope.APP

    @provide
    async def provide_async_engine(
        self,
        dsn: PostgresDsn,
        engine_settings: SqlaEngineSettings,
    ) -> AsyncIterable[AsyncEngine]:
        async_engine_params = {
            "url": dsn,
            **engine_settings.model_dump(),
        }
        async_engine = create_async_engine(**async_engine_params)
        log.debug("Async engine created with DSN: %s", dsn)
        yield async_engine
        log.debug("Disposing async engine...")
        await async_engine.dispose()
        log.debug("Engine is disposed.")

    @provide
    def provide_async_session_maker(
        self,
        engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )
        log.debug("Async session maker initialized.")
        return session_factory


class UserInfrastructureProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def provide_user_async_session(
        self,
        async_session_maker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterable[AsyncSession]:
        log.debug("Starting User async session...")
        async with async_session_maker() as session:
            log.debug("Async session started for User.")
            yield cast(AsyncSession, session)
            log.debug("Closing async session.")
        log.debug("Async session closed for User.")

    unit_of_work = provide(
        source=SqlAlchemyUnitOfWork,
        provides=UnitOfWork,
    )
    event_repository = provide(
        source=EventRepository,
    )
    interactors = provide_all(
        GameDigestInteractor,
    )
