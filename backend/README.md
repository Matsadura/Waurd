## Database seed data

Apply the migrations, then run the deterministic local seed script from this directory:

```bash
uv run alembic upgrade head
uv run python scripts/seed_db.py --reset
```

The script inserts four users, three achievements, one `user_stats` row per user, and seven `user_achievements` rows. It verifies the one-to-one and many-to-many relationships after committing.

Use these credentials to create a session for the authenticated endpoints:

```text
email: alice@example.test
password: SecureP@ssw0rd!123
user id: 00000000-0000-4000-8000-000000000001
```

After logging in, request `GET /api/v1/users/00000000-0000-4000-8000-000000000001/stats` with the returned session cookie.

## Google authentication

Create a Google OAuth web application in Google Cloud Console and add this authorized redirect URI:

```text
http://localhost:8000/api/v1/auth/google/callback
```

Set these backend environment variables before starting the API:

```text
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
GOOGLE_FRONTEND_REDIRECT_URI=http://localhost:3000
```

Start the flow from the frontend by navigating the browser to `GET /api/v1/auth/google`. The callback creates or finds the Google user, sets the existing session and CSRF cookies, and redirects to `GOOGLE_FRONTEND_REDIRECT_URI`.

Apply the OAuth identity constraint before using the flow:

```bash
uv run alembic upgrade head
```

Additional stats test user:

```text
email: stats@email.com
password: SecureP@ssw0rd!123
user id: 00000000-0000-4000-8000-000000000004
```

## Two-factor authentication (email codes)

When 2FA is on, logging in also needs a 6-digit code emailed to the account address. Codes expire after 10 minutes, work once, and stop working after 5 wrong tries. Only one email is sent per user per minute.

### Sending email from Gmail

Gmail needs an app password, not your normal password:

1. Turn on 2-Step Verification for the Google account.
2. Create an app password at https://myaccount.google.com/apppasswords.
3. Add these to `backend/.env`, which is gitignored:

```text
MAIL_USERNAME=your-address@gmail.com
MAIL_PASSWORD=your-16-character-app-password
```

Mail goes through `smtp.gmail.com:587` with STARTTLS by default. Without these settings, the 2FA endpoints answer `503`.

### API flow

Turning 2FA on or off, from a signed-in session (send the `X-CSRF-Token` header):

1. `POST /auth/2fa/code` with `{"action": "enable"}` or `{"action": "disable"}` emails a code.
2. `POST /auth/2fa/enable` or `POST /auth/2fa/disable` with `{"code": "123456"}`.

`GET /auth/2fa` returns `{"enabled": true|false}`.

Logging in once 2FA is on:

- `POST /auth/login` answers `202` with `{"two_factor_required": true, "email_hint": "a***@gmail.com"}` instead of `200`. It emails a code and sets an HttpOnly `two_factor_token` cookie instead of a session.
- Google login redirects to `GOOGLE_FRONTEND_REDIRECT_URI` with `?two_factor=required` added.
- Either way, send `POST /auth/2fa/verify` with `{"code": "123456"}`. On success it returns the user and sets the usual session and CSRF cookies. To get a new code, log in again.

## Password reset (email links)

Uses the same Gmail settings as two-factor authentication. Neither request needs a session or the `X-CSRF-Token` header.

1. `POST /auth/password/forgot` with `{"email": "..."}` always answers `202` with the same message. If the address belongs to an account with a password, a link is emailed after the response is sent, so the response can't be used to tell which emails are registered. Accounts that only use Google sign-in get no link.
2. The link opens `PASSWORD_RESET_URL` (by default `http://localhost:5173/reset-password`) with a `?token=...` query parameter. The frontend reads it and shows a new-password form.
3. `POST /auth/password/reset` with `{"token": "...", "new_password": "..."}` sets the new password and signs the user out of every session. A used, expired, replaced or made-up token returns `400`.

A link works once and expires after 30 minutes. Asking again invalidates the previous link, and each user gets at most one reset email per minute. Only a hash of the token is stored in Redis. If 2FA is on, logging in after a reset still asks for a 2FA code.

## Running the tests

The API tests need no running services: MySQL is replaced by a temporary SQLite database and Redis by fakeredis.

```bash
uv run pytest
uv run pytest --cov --cov-report=term-missing
```

Tests marked `xfail` describe known bugs. They are strict, so fixing a bug makes its test fail until the marker is removed.
