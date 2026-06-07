from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from argon2.exceptions import VerificationError

from .users import ProvidesUser, User

if TYPE_CHECKING:
    from argon2 import PasswordHasher


@dataclass
class AuthenticationFailure:
    reason: str


AuthenticationResult = User | AuthenticationFailure


class PasswordAuthenticator:
    def __init__(
        self,
        user_provider: ProvidesUserWithPasswordHash,
        hasher: PasswordHasher,
    ) -> None:
        self._user_provider = user_provider
        self._hasher = hasher

    def authenticate_user(self, username: str, password: str) -> AuthenticationResult:
        password_hash = self._user_provider.get_password_hash(username)

        if password_hash is None:
            return AuthenticationFailure("User not found")

        try:
            self._hasher.verify(hash=password_hash, password=password)
        except VerificationError as e:
            return AuthenticationFailure(f"Password verification failed: {e}")

        found_user = self._user_provider.get_user_by_username(username)

        if found_user is None:
            return AuthenticationFailure("User not found")

        return found_user


# region Password-related protocols
class ProvidesPasswordHash(Protocol):
    def get_password_hash(self, username: str) -> str | None: ...


class ProvidesUserWithPasswordHash(ProvidesUser, ProvidesPasswordHash): ...


# endregion
