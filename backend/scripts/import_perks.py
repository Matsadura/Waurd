"""Copy the perk catalog (src/backend/game/perks/catalog.csv) into the database.

uv run python scripts/import_perks.py

The app also does this when it starts; run this after editing the CSV to
update the database without a restart.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.core.perk_import import import_perks
from backend.db.session import async_session_maker, engine


async def main() -> int:
    async with async_session_maker() as session:
        report = await import_perks(session)
        await session.commit()
    await engine.dispose()
    print(f"Perks: {report}")
    for label, ids in (
        ("created", report.created),
        ("updated", report.updated),
        ("disabled", report.disabled),
    ):
        if ids:
            print(f"  {label}: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
