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

Additional stats test user:

```text
email: stats@email.com
password: SecureP@ssw0rd!123
user id: 00000000-0000-4000-8000-000000000004
```
