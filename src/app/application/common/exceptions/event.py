from app.infrastructure.exceptions.base import InfrastructureError


class EventProcessingError(InfrastructureError):
    pass


class EventProcessedError(InfrastructureError):
    pass
