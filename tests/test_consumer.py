import asyncio
import logging
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from dishka import Scope
from google.cloud import pubsub_v1

from app.application.common.exceptions.email import EmailDeliveryError
from app.config import Config
from app.domain.entities.pub_sub.entity import PubSubMessage
from app.infrastructure.adapters.pub_sub.pub_sub_event_consumer import PubSubEventConsumer


async def test_consumer_with_no_loop(container, mock_subscriber_client, mock_producer_client):
    with (
        patch(
            "src.app.infrastructure.adapters.pub_sub.pub_sub_event_consumer.pubsub_v1.SubscriberClient",
            return_value=mock_subscriber_client,
        ),
        patch(
            "src.app.infrastructure.adapters.pub_sub.pub_sub_event_producer.pubsub_v1.PublisherClient",
            return_value=mock_producer_client,
        ),
    ):
        async with container(scope=Scope.REQUEST) as request_container:
            mock_config = await request_container.get(Config)
            a = PubSubEventConsumer(container, mock_config)
            loop = None
            try:
                await a.subscribe(loop)
            except RuntimeError as err:
                assert str(err) == "No event loop available in subscriber"


def make_pubsub_message(data: dict | list, attributes: dict | None = None) -> pubsub_v1.subscriber.message.Message:
    """Create a fake PubSubMessage for unit tests."""
    mock_msg = MagicMock(spec=pubsub_v1.subscriber.message.Message)
    mock_msg.data = data
    mock_msg.attributes = attributes or {}
    mock_msg.publish_time = datetime.utcnow()
    mock_msg.ack = Mock()
    mock_msg.nack = Mock()

    # Build your domain object
    return mock_msg


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect, expected_log",
    [
        (TypeError(), "Invalid message for event_type:"),
        (EmailDeliveryError(), "Email error from Google API:"),
        (Exception(), "Error in handle_message:"),
    ],
)
async def test_consumer_process_message(
    container, mock_subscriber_client, mock_producer_client, caplog, side_effect, expected_log
):
    caplog.set_level(logging.ERROR)
    with (
        patch(
            "src.app.infrastructure.adapters.pub_sub.pub_sub_event_consumer.pubsub_v1.SubscriberClient",
            return_value=mock_subscriber_client,
        ),
        patch(
            "src.app.infrastructure.adapters.pub_sub.pub_sub_event_producer.pubsub_v1.PublisherClient",
            return_value=mock_producer_client,
        ),
    ):
        async with container(scope=Scope.REQUEST) as request_container:
            mock_config = await request_container.get(Config)
        a = PubSubEventConsumer(container, mock_config)
        loop = asyncio.get_running_loop()
        a.loop = loop

        await a.subscribe(loop)

        data = b'[{"Italian": "Fiore", "English": "Flower"}]'
        attributes = {"event_type": "DailyDigest"}
        message = make_pubsub_message(data, attributes)
        pub_sub_event = PubSubMessage(message, data, attributes, "DailyDigest", datetime.now())

        fake_future = Mock()
        fake_future.result = Mock(side_effect=side_effect)

        def direct_to_on_done(cb):
            a._on_done(fake_future, pub_sub_event)

        fake_future.add_done_callback = direct_to_on_done

        fake_event = Mock()
        fake_event

        with (
            patch(
                "src.app.infrastructure.adapters.pub_sub.pub_sub_event_consumer.asyncio.run_coroutine_threadsafe",
                return_value=fake_future,
            ),
        ):
            with patch.object(a, "_on_done", wraps=a._on_done):
                a.callback(message)
                assert any(expected_log in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_subscribe_crash(container, mock_subscriber_client, mock_producer_client, caplog):
    mock_subscriber_client.subscribe = Mock(side_effect=[Exception, Mock()])
    caplog.set_level(logging.INFO)
    with (
        patch(
            "src.app.infrastructure.adapters.pub_sub.pub_sub_event_consumer.pubsub_v1.SubscriberClient",
            return_value=mock_subscriber_client,
        ),
        patch(
            "src.app.infrastructure.adapters.pub_sub.pub_sub_event_producer.pubsub_v1.PublisherClient",
            return_value=mock_producer_client,
        ),
    ):
        async with container(scope=Scope.REQUEST) as request_container:
            mock_config = await request_container.get(Config)
        a = PubSubEventConsumer(container, mock_config)
        loop = asyncio.get_running_loop()
        a.loop = loop

        await a.subscribe(loop)
        for rec in caplog.records:
            print(f"[{rec.levelname}] {rec.message}")

        assert any("Failed to start" in rec.message for rec in caplog.records)
        assert any("Attempting to start" in rec.message for rec in caplog.records)
