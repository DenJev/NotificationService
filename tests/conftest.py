import logging
from collections.abc import AsyncGenerator, Iterable
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import pytest_asyncio
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide, provide_all
from google.cloud import pubsub_v1
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.exc import UnmappedClassError
from src.app.infrastructure.sqla_persistence.mappings.event import mapping_registry

from app.application.commands.game_digest import GameDigestInteractor
from app.application.common.ports.email_sender import EmailSender
from app.application.common.ports.unit_of_work import UnitOfWork
from app.application.events.event_dispatcher import EventDispatcher
from app.config import Config
from app.domain.entities.pub_sub.entity import Event
from app.infrastructure.adapters.email.smtp_email_sender import SmtpEmailSender
from app.infrastructure.adapters.pub_sub.pub_sub_event_consumer import PubSubEventConsumer
from app.infrastructure.adapters.pub_sub.pub_sub_event_producer import PubSubEventProducer
from app.infrastructure.sqla_persistence.mappings.all import map_tables
from app.infrastructure.sqla_persistence.mappings.event import metadata
from app.setup.ioc.di_providers.infrastructure import CommonInfrastructureProvider
from app.setup.ioc.di_providers.settings import CommonSettingsProvider


class MockCommonApplicationProvider(Provider):
    scope = Scope.APP

    @provide
    def event_publisher(self) -> PubSubEventProducer:
        mock = MagicMock(spec=PubSubEventProducer)
        return mock

    @provide
    def event_subscriber(self) -> PubSubEventConsumer:
        mock = MagicMock(spec=PubSubEventConsumer)
        return mock

    @provide
    def config(self) -> Config:
        mock = MagicMock(spec=Config)
        mock.PUBSUB_PROJECT_ID = "Slava"
        assert mock.PUBSUB_PROJECT_ID == "Slava"
        mock.GOOGLE_PROJECT_ID = "GOOGLE_PROJECT_ID"
        return mock


class MockUserApplicationProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def build_dispatcher(self) -> EventDispatcher:
        dispatcher = EventDispatcher(container)
        dispatcher.register("DailyDigest", GameDigestInteractor)
        return dispatcher

    @provide
    async def email_sender(self) -> EmailSender:
        mock = MagicMock(spec=EmailSender)
        mock.send = AsyncMock()
        return mock

    @provide
    def unit_of_work(self) -> UnitOfWork:
        mock = MagicMock(spec=UnitOfWork)
        return mock

    interactors = provide_all(
        GameDigestInteractor,
    )


def get_providers() -> Iterable[Provider]:
    return (
        MockCommonApplicationProvider(),
        MockUserApplicationProvider(),
        # UserInfrastructureProvider(),
        CommonInfrastructureProvider(),
        CommonSettingsProvider(),
    )


@pytest.fixture
def mock_subscriber_client() -> MagicMock:
    """Fixture for mocking SubscriberClient."""
    client = MagicMock(spec=pubsub_v1.SubscriberClient)
    client.subscription_path = MagicMock(side_effect=lambda project, sub: f"projects/{project}/subscriptions/{sub}")
    client.get_subscription = Mock()
    client.subscribe = Mock()
    client.close = Mock()
    client.acknowledge = Mock()
    return client


@pytest.fixture
def mock_producer_client() -> MagicMock:
    """Fixture for mocking SubscriberClient."""
    client = MagicMock(spec=pubsub_v1.PublisherClient)
    client.subscription_path = MagicMock(side_effect=lambda project, sub: f"projects/{project}/subscriptions/{sub}")
    client.topic_path = Mock()
    client.create_topic = Mock()
    client.get_topic = Mock()
    return client


@pytest_asyncio.fixture(scope="session")
async def container() -> AsyncGenerator[AsyncContainer]:
    """Create a test dishka container."""
    container = make_async_container(*get_providers())
    yield container
    await container.close()


@pytest_asyncio.fixture
async def smtp(container):
    return await container.get(SmtpEmailSender)


def _is_mapped(cls) -> bool:
    try:
        class_mapper(cls)
        return True
    except UnmappedClassError:
        return False


@pytest.fixture(scope="session", autouse=True)
def setup_mappings():
    # Only run map_tables() if our domain classes aren't mapped yet
    if not _is_mapped(Event):
        map_tables()
        print("Tables after import:", mapping_registry.metadata.tables)
    yield


@pytest.fixture
def dsn() -> str:
    """The database connection string."""
    return "postgresql+psycopg://postgres:changethis@test_db:5432/slava_test"


@pytest_asyncio.fixture
async def engine(dsn: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create a single engine instance for the entire test session."""
    async_engine = create_async_engine(url=dsn)
    yield async_engine
    await async_engine.dispose()


@pytest.fixture
def session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a single session_maker for the entire test session."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def db_session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean, isolated session for each test function."""
    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def db_session_2(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean, isolated session for each test function."""
    async with session_maker() as session:
        yield session


log = logging.getLogger(__name__)


@pytest_asyncio.fixture(autouse=True)
async def clean_db_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        # disable FK constraints temporarily
        await conn.execute(text("SET session_replication_role = 'replica';"))
        print("Tables:", metadata.tables.keys())
        await conn.run_sync(metadata.drop_all)
        await conn.run_sync(metadata.create_all)
        await conn.execute(text("SET session_replication_role = 'origin';"))
    yield
