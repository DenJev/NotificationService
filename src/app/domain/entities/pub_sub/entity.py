import json
from dataclasses import dataclass
from datetime import datetime

from google.cloud import pubsub_v1


@dataclass
class PubSubMessage:
    message: pubsub_v1.subscriber.message.Message
    data: dict
    attributes: dict
    event_type: str | None
    publish_time: datetime

    @classmethod
    def from_pubsub(cls, message: pubsub_v1.subscriber.message.Message) -> "PubSubMessage":
        data = json.loads(message.data.decode("utf-8"))
        attrs = dict(message.attributes)
        event_type = attrs.get("event_type")
        publish_time = message.publish_time
        return cls(message=message, data=data, attributes=attrs, event_type=event_type, publish_time=publish_time)
