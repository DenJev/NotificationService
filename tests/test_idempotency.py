import asyncio
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from dishka import Scope

from app.application.commands.game_digest import GameDigestInteractor
from app.application.common.exceptions.email import EmailDeliveryError
from app.application.common.exceptions.event import EventProcessedError, EventProcessingError
from app.application.common.ports.email_sender import EmailSender
from app.domain.entities.pub_sub.entity import PubSubMessage
from app.domain.entities.pub_sub.value_objects import EventStatus
from app.infrastructure.adapters.database.sqlalc_unit_of_work import SqlAlchemyUnitOfWork

log = logging.getLogger(__name__)


mock_message = SimpleNamespace(
    data=b'{"user_id": 123, "action": "signup"}',
    attributes={"event_type": "DailyDigest", "source": "auth-service"},
    publish_time=datetime.now(timezone.utc),
    message_id="1",
    ack_id="12345",
    ack=lambda: None,  # optional methods Pub/Sub messages usually have
)
msg = PubSubMessage(
    message=mock_message,
    data={"username": "den@hotmail.com", "incorrect_words": [{"Italian": "Fiore", "English": "Flower"}]},
    attributes={"event_type": "DailyDigest", "source": "auth-service"},
    event_type="DailyDigest",
    publish_time=datetime.now(timezone.utc),
    topic="test-topic",
)


class PausingEmailSender:
    """
    A class used only for testing. The purpose is to allow pausing of an asynchronous task at the time of email sending
    so that we can process another consumer before resuming.
    """

    def __init__(self, real_sender, pause_event: asyncio.Event, resume_event: asyncio.Event):
        self.real_sender = real_sender
        self.pause_event = pause_event
        self.resume_event = resume_event

    async def send(self, to, subject, body):
        # Signal pause point
        self.pause_event.set()

        # Wait for resume
        await self.resume_event.wait()

        # Continue real send
        return await self.real_sender.send(to, subject, body)


async def test_2_consumers_processing_at_same_time(container, db_session):
    """
    Here we test two Interactors A and B reacting to a message. Should interactor A be processing a message,
    then consumer B should be aware of this and not process it. Interactor B should result in unack of the message,
    because should interactor A fail, it can reprocess the message.
    """
    pause_event = asyncio.Event()
    resume_event = asyncio.Event()

    uow1 = SqlAlchemyUnitOfWork(db_session)
    uow2 = SqlAlchemyUnitOfWork(db_session)

    async with container(scope=Scope.REQUEST) as request_container:
        real_sender = await request_container.get(EmailSender)
        email_sender = PausingEmailSender(real_sender, pause_event, resume_event)

        interactor1 = GameDigestInteractor(email_sender, uow1)
        interactor2 = GameDigestInteractor(real_sender, uow2)

        task1 = asyncio.create_task(interactor1(msg))

        await pause_event.wait()  # We can alternatively do asyncio.sleep here to hit the wait on the Interactor A.

        with pytest.raises(EventProcessingError):
            await interactor2(msg)

        # Resume interactor A.
        resume_event.set()

        await task1

        final_entry = await uow1.events.get_by_id_and_topic(message_id="1", topic=msg.topic)
        assert final_entry.status == EventStatus.PROCESSED


async def test_2_consumers_processing_at_same_time_during_lock(container, db_session, db_session_2):
    """
    Here we test two Interactors A and B reacting to a message. At the beginning of the BaseInteractor we lock the db
    so that two consumers aren't processing the message at the same time. Once Interactor A locks the db and
    commits it transaction with changing the status of the event to PROCESSING, Interactor B can process the message
    now there is idempotency.
    """
    uow1 = SqlAlchemyUnitOfWork(db_session)
    uow2 = SqlAlchemyUnitOfWork(db_session_2)

    async with container(scope=Scope.REQUEST) as request_container:
        real_sender = await request_container.get(EmailSender)

        interactor1 = GameDigestInteractor(real_sender, uow1)
        interactor2 = GameDigestInteractor(real_sender, uow2)
        async with uow1 as uow_first:
            await interactor1.lock_db(uow_first, msg.topic, msg.message.message_id)

            async with uow2 as uow_scond:
                with pytest.raises(EventProcessingError) as excinfo:
                    await interactor2.lock_db(uow_scond, msg.topic, msg.message.message_id)
                    pass

        assert str(excinfo.value) == "Message 1 is already being processed"


async def test_2_consumers_event_already_processed(container, db_session):
    """
    Here we test two Interactors A and B reacting to a message. Interactor A will already have
    processed the message before interactor B has even seen it.
    """
    uow1 = SqlAlchemyUnitOfWork(db_session)
    uow2 = SqlAlchemyUnitOfWork(db_session)

    async with container(scope=Scope.REQUEST) as request_container:
        real_sender = await request_container.get(EmailSender)
        interactor1 = GameDigestInteractor(real_sender, uow1)
        interactor2 = GameDigestInteractor(real_sender, uow2)

        await interactor1(msg)
        await asyncio.sleep(0.1)

        with pytest.raises(EventProcessedError):
            await interactor2(msg)


async def test_2_consumers_event_A_failed(container, db_session):
    """
    Here we test two Interactors A and B reacting to a message. Interactor A will already have
    processed the message before interactor B
    has even seen it but Interactor A failed on the sending of the email.
    """
    uow1 = SqlAlchemyUnitOfWork(db_session)
    uow2 = SqlAlchemyUnitOfWork(db_session)
    async with container(scope=Scope.REQUEST) as request_container:
        real_sender = await request_container.get(EmailSender)
        real_sender.send = Mock(side_effect=EmailDeliveryError)
        interactor1 = GameDigestInteractor(real_sender, uow1)
        with pytest.raises(EmailDeliveryError):
            await interactor1(msg)
        entry = await uow1.events.get_by_id_and_topic(message_id="1", topic=msg.topic)
        assert entry.status == EventStatus.FAILED
        real_sender.send = AsyncMock()
        interactor2 = GameDigestInteractor(real_sender, uow2)

        await interactor2(msg)
        entry_2 = await uow2.events.get_by_id_and_topic(message_id="1", topic=msg.topic)
        entry_2.status = EventStatus.PROCESSED
