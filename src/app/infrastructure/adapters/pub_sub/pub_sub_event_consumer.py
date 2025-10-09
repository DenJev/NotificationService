import asyncio
import logging
import time

from dishka import AsyncContainer, Scope
from google.api_core.exceptions import NotFound
from google.cloud import pubsub_v1

from app.application.common.exceptions.email import EmailDeliveryError
from app.application.common.ports.event_subscriber import EventConsumer
from app.application.events.event_dispatcher import EventDispatcher
from app.config import Config
from app.domain.entities.pub_sub.entity import PubSubMessage

logger = logging.getLogger(__name__)


class PubSubEventConsumer(EventConsumer):
    def __init__(self, container: AsyncContainer, config: Config):
        self._container = container
        self.project_id = config.GOOGLE_PROJECT_ID
        self.subscriber = pubsub_v1.SubscriberClient()
        self.publisher = pubsub_v1.PublisherClient()
        self.project_id = config.PUBSUB_PROJECT_ID
        self.topic_id = "daily-digest"
        self.subscription_id = "daily-digest-sub"
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_id)
        self.sub_path = self.subscriber.subscription_path(self.project_id, self.subscription_id)
        self.loop = None

    def ensure_subscription(self):
        """
        Makes sure the topic & subscription exist in the emulator.
        I think this is not needed with a real Google Pub/Sub as the topic should be there before
        connecting. The emulator is likely to not have the topic due to restarts.
        """

        try:
            self.publisher.get_topic(request={"topic": self.topic_path})
        except NotFound:
            self.publisher.create_topic(request={"name": self.topic_path})
            logger.info("Created topic: %s", self.topic_path)

        try:
            self.subscriber.get_subscription(request={"subscription": self.sub_path})
        except NotFound:
            self.subscriber.create_subscription(request={"name": self.sub_path, "topic": self.topic_path})
            logger.info("Created subscription: %s", self.sub_path)

    async def _handle_message(self, message: PubSubMessage):
        async with self._container(scope=Scope.REQUEST) as request_container:
            dispatcher = await request_container.get(EventDispatcher)
            dispatcher.container = request_container
            try:
                assert message.event_type
                await dispatcher.dispatch(message.event_type, message.data, message.attributes)
            except TypeError:
                raise

    def _on_done(self, fut: asyncio.Future, event: PubSubMessage):
        """
        Handles acknowledgement of message after processing.
        """
        try:
            fut.result()  # raises if failed
            event.message.ack()
        except TypeError as e:
            logger.error(f"Invalid message for event_type: {event.event_type}%s", e, exc_info=True)
            event.message.ack()
        except EmailDeliveryError as e:
            logger.error(f"Email error from Google API: {event.event_type}%s", e, exc_info=True)
            event.message.ack()
        except Exception as e:
            logger.error("Error in handle_message: %s", e, exc_info=True)
            event.message.nack()
        except KeyboardInterrupt:
            fut.cancel()

    def callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            message = PubSubMessage.from_pubsub(message)
            if not hasattr(self, "loop") or self.loop is None:
                raise RuntimeError("No event loop available in subscriber")

            future = asyncio.run_coroutine_threadsafe(
                self._handle_message(message),
                self.loop,
            )

            future.add_done_callback(lambda fut: self._on_done(fut, message))
        except Exception as e:
            logger.error("Error scheduling message: %s", e, exc_info=True)
            message.nack()

    async def subscribe(self, loop, retry: bool = False):
        if retry:
            logger.info("Attempting to start Pub/Sub listener again: %s")

        self.loop = loop
        if self.loop is None:
            raise RuntimeError("No event loop available in subscriber")
        try:
            self.ensure_subscription()
            streaming_pull_future = self.subscriber.subscribe(self.sub_path, callback=self.callback)
            logger.info("Pub/Sub subscriber started: %s", self.sub_path)

            def wait_for_future(streaming_pull_future):
                try:
                    streaming_pull_future.result()
                except Exception as e:
                    logger.error("Subscriber crashed: %s", e)
                    streaming_pull_future.cancel()
                    time.sleep(5)
                    self.ensure_subscription()  # Only necessary for emulator.
                    streaming_pull_future = self.subscriber.subscribe(self.sub_path, callback=self.callback)
                    self.loop.run_in_executor(None, wait_for_future, streaming_pull_future)

            loop.run_in_executor(None, wait_for_future, streaming_pull_future)

        except Exception as e:
            logger.error("Failed to start Pub/Sub listener: %s", e)
            await self.subscribe(loop, retry=True)
