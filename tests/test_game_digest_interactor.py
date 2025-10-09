import pytest
from dishka import Scope

from app.application.commands.game_digest import GameDigestInteractor
from app.application.common.ports.email_sender import EmailSender


async def test_game_digest_interactor(container):
    async with container(scope=Scope.REQUEST) as request_container:
        smtp = await request_container.get(EmailSender)
        a = GameDigestInteractor(smtp)
        message = {"username": "den@hotmail.com", "incorrect_words": [{"Italian": "Fiore", "English": "Flower"}]}
        await a.__call__(message)


async def test_game_digest_interactor_invalid_message(container):
    async with container(scope=Scope.REQUEST) as request_container:
        smtp = await request_container.get(EmailSender)
        a = GameDigestInteractor(smtp)
        message = {"username": "den@hotmail.com", "invalud_key": [{"Italian": "Fiore", "English": "Flower"}]}
        with pytest.raises(TypeError):
            await a.__call__(message)
