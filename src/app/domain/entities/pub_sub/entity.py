import json
from dataclasses import dataclass
from datetime import datetime

from google.cloud import pubsub_v1

from app.domain.entities.pub_sub.value_objects import EventStatus


@dataclass
class PubSubMessage:
    message: pubsub_v1.subscriber.message.Message
    data: dict
    attributes: dict
    event_type: str
    publish_time: datetime
    topic: str

    @classmethod
    def from_pubsub(cls, message: pubsub_v1.subscriber.message.Message, topic: str) -> "PubSubMessage":
        data = json.loads(message.data.decode("utf-8"))
        attrs = dict(message.attributes)
        event_type = attrs.get("event_type")
        assert isinstance(event_type, str)
        publish_time = message.publish_time
        return cls(
            message=message, data=data, attributes=attrs, event_type=event_type, publish_time=publish_time, topic=topic
        )


# id, message_id, status = (processing, processed), topic, event_type
@dataclass
class Event:
    message_id: str
    topic: str
    event_type: str
    status: EventStatus
    processing_started_at: datetime
    id: int | None = None

    def change_status(self, new_status: EventStatus):
        if not self.status.can_transition_to(new_status):
            raise ValueError(f"Invalid transition from {self.status} to {new_status}")
        self.status = new_status
