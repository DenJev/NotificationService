from sqlalchemy import BIGINT, Column, DateTime, Enum, MetaData, String, Table, UniqueConstraint
from sqlalchemy.orm import registry

from app.domain.entities.pub_sub.entity import Event
from app.domain.entities.pub_sub.value_objects import EventStatus

metadata = MetaData()
mapping_registry = registry(metadata=metadata)
# id, message_id, status = (processing, processed), topic, event_type

event_table = Table(
    "event",
    mapping_registry.metadata,
    Column("id", BIGINT, primary_key=True),
    Column("message_id", String, nullable=False, unique=True),
    Column("topic", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column(
        "status",
        Enum(EventStatus, name="event_status", native_enum=False, validate_strings=True),
        nullable=False,
    ),
    Column("processing_started_at", DateTime, nullable=True),
    UniqueConstraint("message_id", "topic", name="uq_message_topic"),
)


def map_event_table() -> None:
    mapping_registry.map_imperatively(
        Event,
        event_table,
        properties={
            "id": event_table.c.id,
            "message_id": event_table.c.message_id,
            "topic": event_table.c.topic,
            "event_type": event_table.c.event_type,
            "status": event_table.c.status,
            "processing_started_at": event_table.c.processing_started_at,
        },
    )
