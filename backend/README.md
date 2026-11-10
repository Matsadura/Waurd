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

## Running the tests

The API tests need no running services: MySQL is replaced by a temporary SQLite database and Redis by fakeredis.

```bash
uv run pytest
uv run pytest --cov --cov-report=term-missing
```

Tests marked `xfail` describe known bugs. They are strict, so fixing a bug makes its test fail until the marker is removed.
