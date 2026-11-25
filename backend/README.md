## Database seed data

The backend container applies the migrations every time it starts (`alembic upgrade head`). MySQL and Redis are only reachable inside the compose network, so run scripts through the backend container:

```bash
docker compose exec backend python scripts/seed_db.py --reset
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

## Roles

Every user is either `USER` (the default) or `GAME_MASTER`. The role is in every user response (`GET /users/me` and others), so the frontend can show game master tools.

Promote the first game master from the command line:

```bash
docker compose exec backend python scripts/set_role.py someone@example.com GAME_MASTER
```

Game masters can also view any user's profile, stats and matches, and manage users under `/api/v1/admin/users`. Everyone else gets `403`.

- `GET /admin/users?q=&limit=50&offset=0` lists users, newest first. `q` matches part of a username or email.
- `GET /admin/users/{id}` shows one user, including role, sign-in provider and 2FA status.
- `PATCH /admin/users/{id}` changes `username`, `email`, `avatar_url` or `role`. Omitted fields stay the same.
- `DELETE /admin/users/{id}` deletes the user, their friendships, stats and matches, their sessions and their avatar.

Game masters cannot change their own role or delete their own account here, so there is always at least one game master.

## Avatars

- `PUT /users/me/avatar` uploads a PNG, JPEG, WebP or GIF of up to 2 MB as multipart form field `file`. The type is checked from the file's contents, not its name.
- `DELETE /users/me/avatar` removes it.
- `GET /users/{id}/avatar` returns the uploaded image, redirects to an external picture (such as a Google profile photo), or returns a built-in default avatar. Use it as the `src` of every avatar `<img>`.

Uploads are stored under `MEDIA_DIR/avatars` (default `backend/media`, which is gitignored).
