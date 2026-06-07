import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import pyotp
import uvicorn
from argon2 import PasswordHasher
from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, RedirectResponse, Response
from webauthn.helpers import options_to_json_dict

from krabsvault.password_auth import (
    AuthenticationFailure,
    PasswordAuthenticator,
)
from krabsvault.session import SessionManager
from krabsvault.settings import get_settings
from krabsvault.storage import (
    SqliteConnectionManager,
    SqliteCredentialStorage,
    SqliteUserStorage,
)
from krabsvault.webauthn_auth import RelyingParty, WebauthnAuthenticator

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

ASSETS_DIR: Path = Path(__file__).parents[1] / "assets"

# region Application state management & setup
# --- App state ---


class AppState:
    session_manager: SessionManager
    password_authenticator: PasswordAuthenticator
    webauthn_authenticator: WebauthnAuthenticator
    user_storage: SqliteUserStorage
    security_level: str = "password"


app_state = AppState()


# --- App setup ---


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()

    hasher = PasswordHasher()

    connection_manager = SqliteConnectionManager(
        db_path=settings.db_path,
    )

    user_storage = SqliteUserStorage(
        connection_manager=connection_manager,
        hasher=hasher,
    )
    app_state.user_storage = user_storage
    app_state.session_manager = SessionManager(
        user_provider=user_storage,
    )
    app_state.password_authenticator = PasswordAuthenticator(
        user_provider=user_storage,
        hasher=hasher,
    )
    credential_storage = SqliteCredentialStorage(
        connection_manager=connection_manager,
    )

    app_state.webauthn_authenticator = WebauthnAuthenticator(
        relying_party=RelyingParty(
            id=settings.rp_id,
            name=settings.rp_name,
            origin=settings.rp_origin,
        ),
        user_provider=user_storage,
        credential_storage=credential_storage,
    )

    user_storage.save_new_users(users=settings.users)
    yield
    connection_manager.close()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(lifespan=lifespan)
    application.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    application.mount(
        "/static",
        StaticFiles(directory=ASSETS_DIR / "static"),
        name="static",
    )
    return application


# endregion

app = create_app()
templates = Jinja2Templates(directory=ASSETS_DIR / "templates")


# --- Routes ---


@app.get("/", response_model=None)
async def index(request: Request) -> Response:
    user = app_state.session_manager.get_user(request)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        request,
        "vault.html",
        {"user": user, "security_level": app_state.security_level},
    )


# region Admin & API control routes
@app.get("/admin", response_model=None)
async def admin_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"security_level": app_state.security_level},
    )


@app.get("/api/security-level")
async def get_security_level() -> JSONResponse:
    return JSONResponse({"security_level": app_state.security_level})


@app.post("/api/security-level")
async def set_security_level(request: Request) -> JSONResponse:
    body = await request.json()
    level = body.get("level")
    if level not in ("password", "mfa", "passkey"):
        return JSONResponse({"error": "Invalid security level"}, status_code=400)
    app_state.security_level = level
    return JSONResponse(
        {"status": "ok", "security_level": app_state.security_level},
    )


# endregion


# region Password-related routes
@app.get("/login", response_model=None)
async def login_page(request: Request, error: str | None = None) -> Response:
    user = app_state.session_manager.get_user(request)
    if user:
        return RedirectResponse("/")
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": error, "security_level": app_state.security_level},
    )


@app.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> RedirectResponse:
    user = app_state.password_authenticator.authenticate_user(
        username=username,
        password=password,
    )

    if isinstance(user, AuthenticationFailure):
        return RedirectResponse("/login?error=Invalid+credentials", status_code=303)

    if app_state.security_level == "mfa" and user.mfa_enabled:
        request.session["pending_mfa_user_id"] = user.id
        request.session["pending_mfa_username"] = user.username
        return RedirectResponse("/login/mfa", status_code=303)

    app_state.session_manager.set_user(request, user)
    return RedirectResponse("/", status_code=303)


@app.get("/login/mfa", response_model=None)
async def login_mfa_page(request: Request, error: str | None = None) -> Response:
    if "pending_mfa_user_id" not in request.session:
        return RedirectResponse("/login")
    username = request.session.get("pending_mfa_username", "")
    return templates.TemplateResponse(
        request,
        "login_mfa.html",
        {
            "error": error,
            "username": username,
            "security_level": app_state.security_level,
        },
    )


@app.post("/login/mfa/totp")
async def login_mfa_totp(
    request: Request,
    code: Annotated[str, Form()],
) -> RedirectResponse:
    if "pending_mfa_user_id" not in request.session:
        return RedirectResponse("/login")

    if not re.match(r"^\d{6}$", code):
        return RedirectResponse(
            "/login/mfa?error=Code+must+be+6+digits",
            status_code=303,
        )

    user_id = request.session.get("pending_mfa_user_id")
    user = app_state.user_storage.get_user_by_id(user_id)
    if not user or not user.totp_secret:
        return RedirectResponse("/login?error=MFA+not+configured", status_code=303)

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code):
        return RedirectResponse(
            "/login/mfa?error=Invalid+MFA+code",
            status_code=303,
        )

    request.session.pop("pending_mfa_user_id", None)
    request.session.pop("pending_mfa_username", None)
    app_state.session_manager.set_user(request, user)
    return RedirectResponse("/", status_code=303)


@app.get("/mfa/setup", response_model=None)
async def mfa_setup_page(request: Request, error: str | None = None) -> Response:
    user = app_state.session_manager.get_user(request)
    if not user:
        return RedirectResponse("/login")

    secret = request.session.get("temp_totp_secret")
    if not secret:
        secret = pyotp.random_base32()
        request.session["temp_totp_secret"] = secret

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.username,
        issuer_name="KrabsVault",
    )

    return templates.TemplateResponse(
        request,
        "mfa_setup.html",
        {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "error": error,
            "security_level": app_state.security_level,
        },
    )


@app.post("/mfa/setup/verify")
async def mfa_setup_verify(
    request: Request,
    code: Annotated[str, Form()],
) -> RedirectResponse:
    user = app_state.session_manager.get_user(request)
    if not user:
        return RedirectResponse("/login")

    temp_secret = request.session.get("temp_totp_secret")
    if not temp_secret:
        return RedirectResponse("/mfa/setup?error=Session+expired", status_code=303)

    totp = pyotp.TOTP(temp_secret)
    if not totp.verify(code):
        return RedirectResponse(
            "/mfa/setup?error=Invalid+verification+code",
            status_code=303,
        )

    # Save to user storage
    app_state.user_storage.set_totp_secret(user.id, temp_secret)
    app_state.user_storage.set_mfa_enabled(user.id, enabled=True)
    request.session.pop("temp_totp_secret", None)

    return RedirectResponse("/", status_code=303)


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    app_state.session_manager.clear(request)
    return RedirectResponse("/login", status_code=303)


# endregion


# region Webauthn-related routes - Registration
@app.post("/webauthn/register/options")
async def webauthn_register_options(request: Request) -> JSONResponse:
    if app_state.security_level != "passkey":
        return JSONResponse({"error": "WebAuthn disabled"}, status_code=403)

    user = app_state.session_manager.get_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    options = app_state.webauthn_authenticator.create_registration_options(user)
    app_state.session_manager.set_challenge(request, options.challenge)
    return JSONResponse(
        content=options_to_json_dict(options),
    )


@app.post("/webauthn/register/verify")
async def webauthn_register_verify(request: Request) -> JSONResponse:
    if app_state.security_level != "passkey":
        return JSONResponse({"error": "WebAuthn disabled"}, status_code=403)

    user = app_state.session_manager.get_user(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    challenge = app_state.session_manager.get_challenge(request)
    if challenge is None:
        return JSONResponse({"error": "No challenge found"}, status_code=400)

    body = await request.json()
    app_state.webauthn_authenticator.verify_registration(
        credential_json=body,
        expected_challenge=challenge,
        user_id=user.id,
    )
    app_state.session_manager.clear_challenge(request)
    return JSONResponse({"status": "ok"})


# endregion


# region Webauthn-related routes - Authentication
@app.post("/webauthn/login/options")
async def webauthn_login_options(request: Request) -> JSONResponse:
    if app_state.security_level != "passkey":
        return JSONResponse({"error": "WebAuthn disabled"}, status_code=403)

    options = app_state.webauthn_authenticator.create_authentication_options()
    app_state.session_manager.set_challenge(request, options.challenge)
    return JSONResponse(
        content=options_to_json_dict(options),
    )


@app.post("/webauthn/login/verify")
async def webauthn_login_verify(request: Request) -> JSONResponse:
    if app_state.security_level != "passkey":
        return JSONResponse({"error": "WebAuthn disabled"}, status_code=403)

    challenge = app_state.session_manager.get_challenge(request)
    if challenge is None:
        return JSONResponse({"error": "No challenge found"}, status_code=400)

    body = await request.json()
    user = app_state.webauthn_authenticator.verify_authentication(
        credential_json=body,
        expected_challenge=challenge,
    )
    app_state.session_manager.clear_challenge(request)

    app_state.session_manager.set_user(request, user)
    return JSONResponse({"status": "ok"})


# endregion


def main() -> None:
    uvicorn.run("krabsvault.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
