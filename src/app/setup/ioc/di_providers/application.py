# pylint: disable=C0301 (line-too-long)
from dishka import AsyncContainer, Provider, Scope, provide, provide_all

from app.application.commands.game_digest import GameDigestInteractor

# from app.application.common.ports.identity_provider import IdentityProvider
from app.application.common.ports.email_sender import EmailSender
from app.application.common.ports.event_publisher import EventPublisher
from app.application.common.ports.event_subscriber import EventConsumer
from app.application.events.event_dispatcher import EventDispatcher
from app.config import Config
from app.infrastructure.adapters.email.smtp_email_sender import SmtpEmailSender
from app.infrastructure.adapters.pub_sub.pub_sub_event_consumer import PubSubEventConsumer
from app.infrastructure.adapters.pub_sub.pub_sub_event_producer import PubSubEventProducer


def build_dispatcher(container: AsyncContainer) -> EventDispatcher:
    dispatcher = EventDispatcher(container)
    dispatcher.register("DailyDigest", GameDigestInteractor)
    return dispatcher


def build_config(container: AsyncContainer) -> Config:
    return Config.from_env()


class CommonApplicationProvider(Provider):
    scope = Scope.APP

    event_publisher = provide(
        source=PubSubEventProducer,
        provides=EventPublisher,
    )

    event_subscriber = provide(
        source=PubSubEventConsumer,
        provides=EventConsumer,
    )

    configuration = provide(source=build_config, provides=Config)


class UserApplicationProvider(Provider):
    scope = Scope.REQUEST
    dispatcher = provide(
        source=build_dispatcher,
        provides=EventDispatcher,
    )
    smtp_sender = provide(source=SmtpEmailSender, provides=EmailSender)

    # Services
    # Ports

    # Interactors
    interactors = provide_all(
        GameDigestInteractor,
    )
