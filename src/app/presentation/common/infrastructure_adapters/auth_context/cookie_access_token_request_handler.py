# pylint: disable=C0301 (line-too-long)
from fastapi.requests import Request

from app.infrastructure.auth_context.common.ports.access_token_request_handler import (
    AccessTokenRequestHandler,
)
from app.presentation.common.cookie_params import CookieParams


class CookieAccessTokenRequestHandler(AccessTokenRequestHandler):
    def __init__(
        self,
        request: Request,
        cookie_params: CookieParams,
    ):
        self._request = request
        self._cookie_params = cookie_params

    def get_access_token_from_request(self) -> str | None:
        # 1. Try Authorization header first
        auth_header = self._request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[len("Bearer ") :]

        # 2. Fallback to cookie
        return self._request.cookies.get("access_token")

    def add_access_token_to_request(self, new_access_token: str) -> None:
        self._request.state.new_access_token = new_access_token
        self._request.state.cookie_params = {
            "secure": self._cookie_params.secure,
            "samesite": self._cookie_params.samesite,
        }

    def add_refresh_token_to_request(self, new_refresh_token: str) -> None:
        self._request.state.new_refresh_token = new_refresh_token
        self._request.state.cookie_params = {
            "secure": self._cookie_params.secure,
            "samesite": self._cookie_params.samesite,
        }

    def delete_access_token_from_request(self) -> None:
        self._request.state.delete_access_token = True
