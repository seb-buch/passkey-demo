# Passkeys Demo

Live-coding / live-demo app for a presentation on WebAuthn/passkeys.
Two Python apps + an nginx reverse proxy simulate a legitimate site and a phishing attack.

## What it is

| Component | URL | Port | Purpose |
|---|---|---|---|
| **KrabsVault** | `https://krabsvault.com` | 8000 | Legitimate password-manager app |
| **Phishing site** | `https://krabsvau1t.com` | 8666 | Lookalike that silently steals credentials |
| **nginx proxy** | — | 443 | TLS termination + request mirroring for the steal |

The phishing site proxies everything to KrabsVault, but mirrors login/session traffic to the phishing backend to capture passwords, TOTP codes, and session cookies. Passkeys don't get stolen because the RP ID check fails on the wrong origin.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (both Python apps)
- [podman](https://podman.io/) with `podman compose` (runs the nginx container)
- [zellij](https://zellij.dev/) (the demo script opens tabs for each service)
- Google Chrome with a dedicated "Demo-Devoxx" profile (hardcoded as `Profile 2` in the script)
- `/etc/hosts` entries for local TLS to work:
  ```
  127.0.0.1 krabsvault.com
  127.0.0.1 krabsvau1t.com
  ```
- [mkcert](https://github.com/FiloSottile/mkcert) for the TLS certificates — generate them once:
  ```bash
  mkcert -install  # installs the local CA into the system trust store
  cd infra/certs
  mkcert krabsvault.com
  mkcert krabsvau1t.com
  ```

## Running the demo

```bash
# Start everything (cleans DB, starts podman + nginx, opens Chrome, launches services in zellij)
./scripts/demo.sh start

# Tear everything down
./scripts/demo.sh stop
```

The script wipes the SQLite database on each start so the demo always begins from a clean state.

## Credentials

| Username | Password | MFA |
|---|---|---|
| `bob` | `test` | TOTP pre-enrolled (secret in `krabsvault-app/.env`) |

The TOTP secret is stable across DB resets — scan it into your authenticator once.

## Demo flow (rough outline)

1. **Password only** — log in on `krabsvault.com`, then show the phishing site (`krabsvau1t.com`) captured the password.
2. **Password + MFA** — enable MFA, repeat; the TOTP code is also captured (real-time phishing).
3. **Passkey** — register a passkey, repeat; the phishing site can't authenticate because the browser won't sign a challenge for the wrong origin.

## Dev (individual apps)

See `krabsvault-app/README.md` for running KrabsVault standalone on `localhost:8000`.
For the phishing app: `cd phishing-app && uv run phishing` (port 8666).
