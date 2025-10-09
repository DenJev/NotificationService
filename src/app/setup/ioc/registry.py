from typing import Iterable

from dishka import Provider

from app.setup.ioc.di_providers.application import (
    CommonApplicationProvider,
    UserApplicationProvider,
)
from app.setup.ioc.di_providers.infrastructure import (
    CommonInfrastructureProvider,
    UserInfrastructureProvider,
)
from app.setup.ioc.di_providers.settings import (
    CommonSettingsProvider,
)


def get_providers() -> Iterable[Provider]:
    return (
        CommonApplicationProvider(),
        # Domain
        # Application
        UserApplicationProvider(),
        # Infrastructure
        CommonInfrastructureProvider(),
        UserInfrastructureProvider(),
        # Settings
        CommonSettingsProvider(),
    )
