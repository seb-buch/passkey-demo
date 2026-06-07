from dataclasses import dataclass
from typing import Protocol


@dataclass
class User:
    id: int
    username: str
    display_name: str
    user_handle: bytes  # random opaque identifier used during WebAuthn ceremonies
    totp_secret: str | None = None
    mfa_enabled: bool = False


@dataclass
class NewUser:
    username: str
    display_name: str
    password: str  # plaintext, hashed at storage time


# region User-related protocols
class ProvidesUser(Protocol):
    def get_user_by_id(self, user_id: int) -> User | None: ...
    def get_user_by_username(self, username: str) -> User | None: ...
    def get_user_by_handle(self, user_handle: bytes) -> User | None: ...


class SavesNewUsers(Protocol):
    def save_new_users(self, users: list[NewUser]) -> None: ...


class UserStorage(ProvidesUser, SavesNewUsers): ...


# endregion
