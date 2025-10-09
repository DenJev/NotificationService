# pylint: disable=C0301 (line-too-long)
from dishka import Provider, Scope, from_context, provide

from app.setup.config.settings import AppSettings, PostgresDsn, SqlaEngineSettings


class CommonSettingsProvider(Provider):
    scope = Scope.APP

    settings = from_context(provides=AppSettings)

    @provide
    def provide_postgres_dsn(self, settings: AppSettings) -> PostgresDsn:
        return PostgresDsn(settings.postgres.dsn)

    @provide
    def provide_sqla_engine_settings(self, settings: AppSettings) -> SqlaEngineSettings:
        return settings.sqla
