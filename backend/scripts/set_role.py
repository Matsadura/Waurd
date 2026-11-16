"""Give a user a role. Use it to create the first game master.

uv run python scripts/set_role.py someone@example.com GAME_MASTER
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select

from backend.db.session import async_session_maker, engine
from backend.models import User, UserRole


async def set_role(email: str, role: UserRole) -> int:
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No user with email {email}", file=sys.stderr)
            return 1
        user.role = role
        await session.commit()
        print(f"{user.username} is now {role.value}")
    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument("role", choices=[role.value for role in UserRole])
    args = parser.parse_args()
    raise SystemExit(asyncio.run(set_role(args.email, UserRole(args.role))))


if __name__ == "__main__":
    main()
