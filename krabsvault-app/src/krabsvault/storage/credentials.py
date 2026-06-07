from typing import TYPE_CHECKING, override

from krabsvault.webauthn_auth import (
    WebauthnCredential,
    WebauthnCredentialStorage,
)

if TYPE_CHECKING:
    from krabsvault.storage.users import SqliteConnectionManager


class SqliteCredentialStorage(WebauthnCredentialStorage):
    _CREDENTIAL_COLUMNS = "id, public_key, sign_count, user_id"

    def __init__(
        self,
        connection_manager: SqliteConnectionManager,
    ) -> None:
        self._connection_manager = connection_manager
        self._initialize_credentials_table()

    def _initialize_credentials_table(self) -> None:
        with self._connection_manager.connection as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS credentials
                (
                    id         BLOB PRIMARY KEY,
                    public_key BLOB NOT NULL,
                    sign_count INTEGER NOT NULL DEFAULT 0,
                    user_id    INTEGER NOT NULL REFERENCES users(id)
                )
                """,
            )

    @override
    def save_credential(self, credential: WebauthnCredential) -> None:
        with self._connection_manager.connection as connection:
            connection.execute(
                """
                INSERT INTO credentials (id, public_key, sign_count, user_id)
                VALUES (?, ?, ?, ?)
                """,
                (
                    credential.id,
                    credential.public_key,
                    credential.signature_count,
                    credential.user_id,
                ),
            )

    @override
    def get_credentials_by_user_id(
        self,
        user_id: int,
    ) -> list[WebauthnCredential]:
        with self._connection_manager.connection as connection:
            rows = connection.execute(
                f"SELECT {self._CREDENTIAL_COLUMNS} FROM credentials WHERE user_id = ?",  # noqa: S608
                (user_id,),
            ).fetchall()
        return [
            WebauthnCredential(
                id=row["id"],
                public_key=row["public_key"],
                signature_count=row["sign_count"],
                user_id=row["user_id"],
            )
            for row in rows
        ]

    @override
    def get_credential_by_id(
        self,
        credential_id: bytes,
    ) -> WebauthnCredential | None:
        with self._connection_manager.connection as connection:
            row = connection.execute(
                f"SELECT {self._CREDENTIAL_COLUMNS} FROM credentials WHERE id = ?",  # noqa: S608
                (credential_id,),
            ).fetchone()
        if row is None:
            return None
        return WebauthnCredential(
            id=row["id"],
            public_key=row["public_key"],
            signature_count=row["sign_count"],
            user_id=row["user_id"],
        )

    @override
    def update_signature_count(
        self,
        credential_id: bytes,
        signature_count: int,
    ) -> None:
        with self._connection_manager.connection as connection:
            connection.execute(
                "UPDATE credentials SET sign_count = ? WHERE id = ?",
                (signature_count, credential_id),
            )
