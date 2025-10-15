from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from dishka import Scope

from app.application.commands.game_digest import GameDigestInteractor
from app.application.common.ports.email_sender import EmailSender
from app.application.common.ports.unit_of_work import UnitOfWork
import os

from app.domain.entities.pub_sub.entity import PubSubMessage
from app.infrastructure.adapters.database.sqlalc_unit_of_work import SqlAlchemyUnitOfWork
print("CWD:", os.getcwd())
print("TEST FILE:", __file__)
SqlAlchemyUnitOfWork
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
async def test_game_digest_interactor(container, db_session):
    uow1 = SqlAlchemyUnitOfWork(db_session)
    async with container(scope=Scope.REQUEST) as request_container:
        smtp = await request_container.get(EmailSender)
        a = GameDigestInteractor(smtp, uow1)
        await a.__call__(msg)


async def test_game_digest_interactor_invalid_message(container,db_session):
    uow1 = SqlAlchemyUnitOfWork(db_session)
    async with container(scope=Scope.REQUEST) as request_container:
        smtp = await request_container.get(EmailSender)
        a = GameDigestInteractor(smtp, uow1)
        msg.data = {"username": "den@hotmail.com", "invalud_key": [{"Italian": "Fiore", "English": "Flower"}]}
        with pytest.raises(TypeError):
            await a.__call__(msg)
