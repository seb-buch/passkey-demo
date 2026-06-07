# KrabsVault

Demo app for a live coding presentation on WebAuthn/passkeys.

## Stack

- **Python 3.14** / **FastAPI** with Jinja2 templates
- **SQLite** (raw `sqlite3`, no ORM)
- **argon2** for password hashing
- **py_webauthn** for passkey registration and authentication
- **uv** as package manager

## Getting started

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# Clone and enter the project
git clone https://github.com/seb-buch/krabsvault.git
cd krabsvault

# Install dependencies
uv sync

# Copy the env template and adjust if needed
cp env.example .env

# Run the dev server
uv run uvicorn krabsvault.app:app --reload
```

The app is available at [http://localhost:8000](http://localhost:8000).

### Default credentials

The `env.example` seeds a single user:

| Username | Password |
|----------|----------|
| `bob`    | `test`   |

### WebAuthn / Passkeys

The default `env.example` is configured for local development (`RP_ID=localhost`,
`RP_ORIGIN=http://localhost:8000`). If you deploy the app or use a custom domain, update the `RP_ID`
and `RP_ORIGIN` settings accordingly.

## Project structure

```
src/
  krabsvault/              # Python package
    app.py                 # FastAPI app, routes, lifespan setup
    password_auth.py       # Password authentication (argon2)
    session.py             # Cookie-based session management
    settings.py            # Config via pydantic-settings (.env)
    storage/               # SQLite storage
      credentials.py       #   WebAuthn credentials
      users.py             #   Users + connection manager
    users.py               # Domain models and protocols
    webauthn_auth.py       # Passkey registration & authentication
  assets/
    static/                # JS, images
    templates/             # Jinja2 HTML templates
```

## Dev commands

```bash
uv run krabsvault                                # run dev server
uv run uvicorn krabsvault.app:app --reload       # run dev server (with reload)
uv run ruff check .                          # lint
uv run ruff format .                         # format
```

## License

This is a demo app for educational purposes.
