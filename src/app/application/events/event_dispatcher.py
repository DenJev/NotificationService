class EventDispatcher:
    def __init__(self, container):
        self.container = container
        self._handlers = {}

    def register(self, event_type: str, interactor) -> None:
        self._handlers[event_type] = interactor

    async def dispatch(self, event_type: str, data: dict, attrs: dict):
        interactor_cls = self._handlers.get(event_type)
        async with self.container() as request:
            interactor = await request.get(interactor_cls)
            await interactor.__call__(data)
