from typing import TYPE_CHECKING

from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

if TYPE_CHECKING:
    from starlette.requests import Request

    from krabsvault.users import ProvidesUser, User


class SessionManager:
    _USER_ID_FIELD = "user_id"
    _CHALLENGE_FIELD = "webauthn_challenge"

    def __init__(self, user_provider: ProvidesUser) -> None:
        self._user_provider = user_provider

    def set_user(self, request: Request, user: User) -> None:
        request.session[self._USER_ID_FIELD] = user.id

    def get_user(self, request: Request) -> User | None:
        user_id = request.session.get(self._USER_ID_FIELD)
        if not isinstance(user_id, int):
            return None
        return self._user_provider.get_user_by_id(user_id)

    def set_challenge(self, request: Request, challenge: bytes) -> None:
        request.session[self._CHALLENGE_FIELD] = bytes_to_base64url(challenge)

    def get_challenge(self, request: Request) -> bytes | None:
        value = request.session.get(self._CHALLENGE_FIELD)
        if not isinstance(value, str):
            return None
        return base64url_to_bytes(value)

    def clear_challenge(self, request: Request) -> None:
        request.session.pop(self._CHALLENGE_FIELD, None)

    @staticmethod
    def clear(request: Request) -> None:
        request.session.clear()
