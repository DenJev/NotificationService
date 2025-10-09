# pylint: disable=C0301 (line-too-long)
__all__ = (
    "create_app",
    "configure_app",
    "create_async_ioc_container",
)

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Iterable

from dishka import AsyncContainer, Provider, make_async_container
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from google.cloud import pubsub_v1

from app.application.common.ports.event_subscriber import EventConsumer
from app.infrastructure.sqla_persistence.mappings.all import map_tables
from app.presentation.common.asgi_auth_middleware import ASGIAuthMiddleware
from app.presentation.common.exception_handler import ExceptionHandler
from app.setup.config.settings import AppSettings

log = logging.getLogger(__name__)
# Pub/Sub config
project_id = os.getenv("PUBSUB_PROJECT_ID", "slava")
topic_id = "daily-digest"
subscription_id = "daily-digest-sub"
subscriber: pubsub_v1.SubscriberClient | None = None
streaming_pull_future = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    map_tables()
    loop = asyncio.get_running_loop()
    app.state.loop = loop

    event_subscriber = await app.state.dishka_container.get(EventConsumer)
    await event_subscriber.subscribe(loop)

    # Hand control back to FastAPI
    yield

    # 👋 Shutdown
    try:
        if streaming_pull_future:
            streaming_pull_future.cancel()
            log.info("Pub/Sub subscriber stopped")
        if subscriber:
            subscriber.close()
    except Exception as e:
        log.error("Error during Pub/Sub shutdown: %s", e)

    await app.state.dishka_container.close()  # noqa


def create_app() -> FastAPI:
    return FastAPI(
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )


def configure_app(
    app: FastAPI,
    root_router: APIRouter,
) -> None:
    app.include_router(root_router)
    app.add_middleware(ASGIAuthMiddleware)  # noqa
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://app.localhost:3000",
            "http://app.localhost",
            "http://app.localhost/",
        ],  # React dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    exception_handler = ExceptionHandler(app)
    exception_handler.setup_handlers()


def create_async_ioc_container(
    providers: Iterable[Provider],
    settings: AppSettings,
) -> AsyncContainer:
    return make_async_container(
        *providers,
        context={AppSettings: settings},
    )
