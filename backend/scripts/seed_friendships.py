import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_session_maker
from backend.models.friendship import Friendship, FriendshipStatus
from backend.models.user import OAuthProvider, User


async def seed_data():
    """
    Seeds initial test users and friendship relationships into MySQL using async_session_maker.
    """
    async with async_session_maker() as session:  # type: AsyncSession
        print("🌱 Starting database seed...")

        # 1. Define sample users
        user_definitions = [
            {
                "username": "alice",
                "email": "alice@waurd.game",
                "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjO5E/xG/1/1/1/1/1/1/1/1/1/1/1",
            },
            {
                "username": "bob",
                "email": "bob@waurd.game",
                "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjO5E/xG/1/1/1/1/1/1/1/1/1/1/1",
            },
            {
                "username": "charlie",
                "email": "charlie@waurd.game",
                "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjO5E/xG/1/1/1/1/1/1/1/1/1/1/1",
            },
            {
                "username": "diana",
                "email": "diana@waurd.game",
                "password_hash": "$2b$12$eImiTXuWVxfM37uY4JANjO5E/xG/1/1/1/1/1/1/1/1/1/1/1",
            },
        ]

        created_users = {}

        # 2. Insert or fetch existing users
        for u_data in user_definitions:
            stmt = select(User).where(User.username == u_data["username"])
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                user_id_bytes = uuid.uuid4().bytes
                user = User(
                    id=user_id_bytes,
                    username=u_data["username"],
                    email=u_data["email"],
                    password_hash=u_data["password_hash"],
                    oauth_provider=OAuthProvider.LOCAL,
                    is_online=True,
                    created_at=datetime.utcnow(),
                )
                session.add(user)
                created_users[u_data["username"]] = user
                print(f"  + Created user: {u_data['username']}")
            else:
                created_users[u_data["username"]] = existing_user
                print(f"  ~ User already exists: {u_data['username']}")

        await session.commit()

        alice = created_users["alice"]
        bob = created_users["bob"]
        charlie = created_users["charlie"]
        diana = created_users["diana"]

        # 3. Define friendship scenarios
        friendship_scenarios = [
            # Alice and Bob are accepted friends
            {
                "requester_id": alice.id,
                "addressee_id": bob.id,
                "status": FriendshipStatus.ACCEPTED,
                "desc": "Alice <-> Bob (ACCEPTED)",
            },
            # Alice sent a pending request to Charlie
            {
                "requester_id": alice.id,
                "addressee_id": charlie.id,
                "status": FriendshipStatus.PENDING,
                "desc": "Alice -> Charlie (PENDING)",
            },
            # Diana sent a pending request to Alice
            {
                "requester_id": diana.id,
                "addressee_id": alice.id,
                "status": FriendshipStatus.PENDING,
                "desc": "Diana -> Alice (PENDING)",
            },
            # Bob blocked Charlie
            {
                "requester_id": bob.id,
                "addressee_id": charlie.id,
                "status": FriendshipStatus.BLOCKED,
                "desc": "Bob -x Charlie (BLOCKED)",
            },
        ]

        # 4. Insert friendships if they don't exist
        for scenario in friendship_scenarios:
            stmt = select(Friendship).where(
                Friendship.requester_id == scenario["requester_id"],
                Friendship.addressee_id == scenario["addressee_id"],
            )
            result = await session.execute(stmt)
            existing_friendship = result.scalar_one_or_none()

            if not existing_friendship:
                friendship = Friendship(
                    requester_id=scenario["requester_id"],
                    addressee_id=scenario["addressee_id"],
                    status=scenario["status"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(friendship)
                print(f"  + Created friendship: {scenario['desc']}")
            else:
                print(f"  ~ Friendship exists: {scenario['desc']}")

        await session.commit()
        print("✅ Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
