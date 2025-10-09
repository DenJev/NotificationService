from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import pubsub_v1

from app.application.common.ports.event_publisher import EventPublisher
from app.config import Config

config = Config.from_env()


class PubSubEventProducer(EventPublisher):
    def __init__(self):
        self.project_id = config.GOOGLE_PROJECT_ID
        self.publisher = pubsub_v1.PublisherClient()

    def _ensure_topic(self, topic_name: str) -> str:
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        try:
            self.publisher.get_topic(request={"topic": topic_path})
        except NotFound:
            try:
                self.publisher.create_topic(request={"name": topic_path})
            except AlreadyExists:
                pass
        return topic_path

    def publish(self, topic_name: str, message: str, **attrs):
        self._ensure_topic(topic_name)
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        future = self.publisher.publish(topic_path, message.encode("utf-8"), **attrs)
        return future.result()
