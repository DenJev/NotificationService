from collections.abc import AsyncGenerator, Iterable
from unittest.mock import MagicMock, Mock

import pytest
import pytest_asyncio
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide, provide_all
from google.cloud import pubsub_v1

from app.application.commands.game_digest import GameDigestInteractor
from app.application.common.ports.email_sender import EmailSender
from app.application.events.event_dispatcher import EventDispatcher
from app.config import Config
from app.infrastructure.adapters.pub_sub.pub_sub_event_consumer import PubSubEventConsumer
from app.infrastructure.adapters.pub_sub.pub_sub_event_producer import PubSubEventProducer
from app.infrastructure.adapters.email.smtp_email_sender import SmtpEmailSender


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
    def email_sender(self) -> EmailSender:
        mock = MagicMock(spec=EmailSender)
        return mock

    interactors = provide_all(
        GameDigestInteractor,
    )


def get_providers() -> Iterable[Provider]:
    return (
        MockCommonApplicationProvider(),
        MockUserApplicationProvider(),
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
