from enum import Enum


class EventStatus(Enum):
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    PROCESSED = "PROCESSED"

    def can_transition_to(self, new_status: "EventStatus") -> bool:
        allowed = {
            EventStatus.PROCESSING: [EventStatus.FAILED, EventStatus.PROCESSED],
            EventStatus.FAILED: [EventStatus.PROCESSING],
            EventStatus.PROCESSED: [],
        }
        return new_status in allowed[self]
