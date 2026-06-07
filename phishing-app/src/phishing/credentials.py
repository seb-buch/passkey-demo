from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class CapturedCredential:
    username: str
    password: str
    n_captures: int = 1
    last_captured_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


captured_credentials: list[CapturedCredential] = []


def capture_credential(username: str, password: str) -> CapturedCredential:
    for credential in captured_credentials:
        if credential.username == username and credential.password == password:
            credential.n_captures += 1
            credential.last_captured_at = datetime.now(tz=UTC)
            return credential

    credential = CapturedCredential(username=username, password=password)
    captured_credentials.append(credential)
    return credential
