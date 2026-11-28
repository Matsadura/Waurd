from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.exceptions import BadRequestException
from backend.game.balance import MAX_LOADOUT_SLOTS
from backend.models.achievements import Achievement
from backend.models.perk import Perk
from backend.models.user_achievements import UserAchievement
from backend.models.user_loadout import UserLoadout
from backend.repositories.base import BaseRepository


class PerkRepository(BaseRepository[Perk]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Perk, session)

    async def get_all_perks(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[Perk], int]:
        total = (
            await self.session.execute(select(func.count()).select_from(Perk))
        ).scalar_one()

        stmt = (
            select(Perk)
            .order_by(Perk.id.asc())  # or Perk.name.asc()
            .offset(skip)
            .limit(limit)
        )
        perks = list((await self.session.execute(stmt)).scalars().all())
        return perks, total

    async def get_all_achievements(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[Achievement], int]:
        total = (
            await self.session.execute(select(func.count()).select_from(Achievement))
        ).scalar_one()

        stmt = (
            select(Achievement)
            .options(selectinload(Achievement.reward_perk))
            .order_by(Achievement.id.asc())
            .offset(skip)
            .limit(limit)
        )
        achievements = list((await self.session.execute(stmt)).scalars().all())
        return achievements, total

    async def get_user_achievements_progress(self, user_id: bytes) -> list[dict]:
        """
        Fetch only achievements that the user has actual progress on.
        If the user has not started any achievements, returns an empty list.
        """
        stmt = (
            select(UserAchievement)
            .options(
                selectinload(UserAchievement.achievement).selectinload(
                    Achievement.reward_perk
                )
            )
            .where(UserAchievement.user_id == user_id)
            .order_by(
                UserAchievement.is_completed.desc(),
                UserAchievement.current_progress.desc(),
            )
        )
        result = await self.session.execute(stmt)
        user_achievements = result.scalars().all()

        progress_list = []
        for ua in user_achievements:
            ach = ua.achievement
            if not ach:
                continue

            target = ach.target_value if ach.target_value > 0 else 1
            if ua.is_completed:
                pct = 100.0
            else:
                pct = max(
                    0.0,
                    min(100.0, round((ua.current_progress / target) * 100, 1)),
                )

            progress_list.append(
                {
                    "achievement_id": ach.id,
                    "name": ach.name,
                    "description": ach.description,
                    "icon_url": ach.icon_url,
                    "xp_reward": ach.xp_reward,
                    "target_value": ach.target_value,
                    "current_progress": ua.current_progress,
                    "is_completed": ua.is_completed,
                    "progress_percentage": pct,
                    "unlocked_at": ua.unlocked_at if ua.is_completed else None,
                    "reward_perk_id": ach.reward_perk_id,
                    "reward_perk": ach.reward_perk,
                }
            )

        return progress_list

    async def get_user_unlocked_perks(self, user_id: bytes) -> Sequence[Perk]:
        """
        Fetch all perks unlocked by the user through completed achievements.
        Performs a single direct SQL JOIN query without Python loops.
        """
        stmt = (
            select(Perk)
            .distinct()
            .join(Achievement, Achievement.reward_perk_id == Perk.id)
            .join(
                UserAchievement,
                UserAchievement.achievement_id == Achievement.id,
            )
            .where(
                UserAchievement.user_id == user_id,
                UserAchievement.is_completed.is_(True),
            )
            .order_by(Perk.name.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_user_loadout(self, user_id: bytes) -> dict:
        """Fetch the user's active equipped perks and all unlocked perks."""
        unlocked_perks = await self.get_user_unlocked_perks(user_id)

        stmt = (
            select(UserLoadout)
            .options(selectinload(UserLoadout.perk))
            .where(UserLoadout.user_id == user_id)
            .order_by(UserLoadout.created_at.asc())
        )
        res = await self.session.execute(stmt)
        loadout_rows = res.scalars().all()

        equipped_perks = [row.perk for row in loadout_rows if row.perk is not None]

        return {
            "max_slots": MAX_LOADOUT_SLOTS,
            "equipped_perks": equipped_perks,
            "unlocked_perks": list(unlocked_perks),
        }

    async def update_user_loadout(self, user_id: bytes, perk_ids: list[str]) -> dict:
        """
        Equip or configure active persistent starter perks before queuing.
        Validates that at most MAX_LOADOUT_SLOTS perks are equipped, no duplicates,
        and that every perk has been unlocked by the user.
        """
        if len(perk_ids) > MAX_LOADOUT_SLOTS:
            raise BadRequestException(
                f"Cannot equip more than {MAX_LOADOUT_SLOTS} starter perks in your loadout."
            )

        if len(perk_ids) != len(set(perk_ids)):
            raise BadRequestException("Duplicate perks cannot be equipped.")

        unlocked_perks = await self.get_user_unlocked_perks(user_id)
        unlocked_ids = {p.id for p in unlocked_perks}

        for pid in perk_ids:
            if pid not in unlocked_ids:
                raise BadRequestException(
                    f"Perk '{pid}' is locked or does not exist. Complete its achievement to unlock it."
                )

        # Clear existing loadout for this user
        del_stmt = delete(UserLoadout).where(UserLoadout.user_id == user_id)
        await self.session.execute(del_stmt)

        # Insert new equipped perks
        for pid in perk_ids:
            self.session.add(UserLoadout(user_id=user_id, perk_id=pid))

        await self.session.flush()

        return await self.get_user_loadout(user_id)
