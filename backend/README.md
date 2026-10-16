## Database seed data

Apply the migrations, then run the deterministic local seed script from this directory:

```bash
uv run alembic upgrade head
uv run python scripts/seed_db.py --reset
```

The script inserts three users, three achievements, one `user_stats` row per user, and six `user_achievements` rows. It verifies the one-to-one and many-to-many relationships after committing.
