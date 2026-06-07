from functools import lru_cache
from pathlib import Path
from secrets import token_hex

from pydantic_settings import BaseSettings, SettingsConfigDict

from krabsvault.users import (
    NewUser,  # noqa: TC001 - Needed for runtime model validation
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    db_path: Path = Path("vault.db")
    secret_key: str = token_hex(32)  # noqa: S105
    users: list[NewUser] = []
    rp_id: str = "localhost"
    rp_name: str = "KrabsVault"
    rp_origin: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
