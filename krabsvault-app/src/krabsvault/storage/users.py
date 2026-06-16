import os
import sqlite3
from typing import TYPE_CHECKING, override

from krabsvault.password_auth import ProvidesUserWithPasswordHash
from krabsvault.users import NewUser, SavesNewUsers, User

if TYPE_CHECKING:
    from pathlib import Path

    from argon2 import PasswordHasher


class SqliteConnectionManager:
    def __init__(self, db_path: Path) -> None:
        self._connection = sqlite3.connect(database=db_path, timeout=5.0)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.row_factory = sqlite3.Row

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def close(self) -> None:
        self._connection.close()


class SqliteUserStorage(ProvidesUserWithPasswordHash, SavesNewUsers):
    _USER_COLUMNS = "id, username, display_name, user_handle, totp_secret, mfa_enabled"

    def __init__(
        self,
        connection_manager: SqliteConnectionManager,
        hasher: PasswordHasher,
    ) -> None:
        self._connection_manager = connection_manager
        self._hasher = hasher
        self._initialize_database()

    def _initialize_database(self) -> None:
        with self._connection_manager.connection as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users
                (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT NOT NULL UNIQUE,
                    display_name  TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    user_handle   BLOB NOT NULL UNIQUE,
                    totp_secret   TEXT,
                    mfa_enabled   INTEGER NOT NULL DEFAULT 0
                )
                """,
            )

    @override
    def save_new_users(self, users: list[NewUser]) -> None:
        with self._connection_manager.connection as connection:
            for user in users:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO users
                    (username, display_name, password_hash, user_handle,
                     totp_secret, mfa_enabled)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user.username,
                        user.display_name,
                        self._hasher.hash(user.password),
                        os.urandom(64),
                        user.totp_secret,
                        int(user.mfa_enabled),
                    ),
                )

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            user_handle=row["user_handle"],
            totp_secret=row["totp_secret"],
            mfa_enabled=bool(row["mfa_enabled"]),
        )

    def set_totp_secret(self, user_id: int, totp_secret: str | None) -> None:
        with self._connection_manager.connection as connection:
            connection.execute(
                "UPDATE users SET totp_secret = ? WHERE id = ?",
                (totp_secret, user_id),
            )

    def set_mfa_enabled(self, user_id: int, *, enabled: bool) -> None:
        with self._connection_manager.connection as connection:
            connection.execute(
                "UPDATE users SET mfa_enabled = ? WHERE id = ?",
                (1 if enabled else 0, user_id),
            )

    @override
    def get_user_by_id(self, user_id: int) -> User | None:
        with self._connection_manager.connection as connection:
            row = connection.execute(
                f"SELECT {self._USER_COLUMNS} FROM users WHERE id = ?",  # noqa: S608
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    @override
    def get_user_by_username(self, username: str) -> User | None:
        with self._connection_manager.connection as connection:
            row = connection.execute(
                f"SELECT {self._USER_COLUMNS} FROM users WHERE username = ?",  # noqa: S608
                (username,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    @override
    def get_user_by_handle(self, user_handle: bytes) -> User | None:
        with self._connection_manager.connection as connection:
            row = connection.execute(
                f"SELECT {self._USER_COLUMNS} FROM users WHERE user_handle = ?",  # noqa: S608
                (user_handle,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_user(row)

    @override
    def get_password_hash(self, username: str) -> str | None:
        with self._connection_manager.connection as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return row["password_hash"]
