import os
from dataclasses import dataclass

from dotenv import load_dotenv


# pylint: disable=C0103
@dataclass
class Config:
    GOOGLE_PROJECT_ID: str | None
    PUBSUB_PROJECT_ID: str | None
    EMAIL_USERNAME: str | None

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        return cls(
            GOOGLE_PROJECT_ID=os.getenv("GOOGLE_PROJECT_ID", ""),
            PUBSUB_PROJECT_ID=os.getenv("PUBSUB_PROJECT_ID", "slava"),
            EMAIL_USERNAME=os.getenv("EMAIL_USERNAME", ""),
        )
