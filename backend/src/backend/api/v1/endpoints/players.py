"""Other players' public profiles, for clicking a username in Friends, Duels or
the leaderboards. Read-only, and only safe fields: your own private data stays
under /users."""

from uuid import UUID

from backend.api.dependencies.auth import get_current_user
from backend.core.exceptions import EntityNotFoundException
from backend.db.uow import UnitOfWork
from backend.models.achievements import Achievement
from backend.models.friendship import FriendshipStatus
from backend.models.match import MatchStatus
from backend.models.user import User
from backend.models.user_achievements import UserAchievement
from backend.repositories.friendship import FriendshipRepository
from backend.schemas.match import MatchResponse
from backend.schemas.pagination import PaginatedResponse
from backend.schemas.player import PublicAchievement, PublicPlayerResponse
from backend.schemas.user import UserStatsResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

router = APIRouter(prefix="/players", tags=["Players"])


async def _visible_player(
    uow: UnitOfWork, viewer: User, player_id: UUID
) -> tuple[User, FriendshipStatus | None]:
    """The player and how the viewer is linked to them. A block either way
    hides the profile, like a missing player."""
    player = await uow.users.get_by_id(player_id.bytes)
    link = None
    if player is not None and player.id != viewer.id:
        link = await FriendshipRepository(uow.session).get_by_users(
            viewer.id, player.id
        )
    if player is None or (link is not None and link.status == FriendshipStatus.BLOCKED):
        raise EntityNotFoundException("Player not found")
    return player, None if link is None else link.status


@router.get("/{player_id}", response_model=PublicPlayerResponse)
async def get_player(
    player_id: UUID,
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> PublicPlayerResponse:
    """A player's public profile: name, avatar, level, stats and completed
    achievements. Online status only if you're friends (or it's you)."""
    async with uow:
        player, link = await _visible_player(uow, current_user, player_id)
        stats = await uow.user_stats.get_by_user_id(player.id)
        rows = await uow.session.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, Achievement.id == UserAchievement.achievement_id)
            .where(
                UserAchievement.user_id == player.id,
                UserAchievement.is_completed.is_(True),
            )
            .order_by(UserAchievement.unlocked_at.desc())
        )
        sees_presence = (
            player.id == current_user.id or link == FriendshipStatus.ACCEPTED
        )
        return PublicPlayerResponse(
            id=player.id,
            username=player.username,
            avatar_url=player.avatar_url,
            created_at=player.created_at,
            xp=player.xp,
            level=player.level,
            is_online=player.is_online if sees_presence else None,
            last_seen_at=player.last_seen_at if sees_presence else None,
            stats=None if stats is None else UserStatsResponse.model_validate(stats),
            achievements=[
                PublicAchievement(
                    achievement_id=achievement.id,
                    name=achievement.name,
                    description=achievement.description,
                    icon_url=achievement.icon_url,
                    xp_reward=achievement.xp_reward,
                    unlocked_at=progress.unlocked_at,
                )
                for progress, achievement in rows
            ],
        )


@router.get("/{player_id}/matches", response_model=PaginatedResponse[MatchResponse])
async def get_player_matches(
    player_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    match_status: MatchStatus | None = Query(
        None, alias="status", description="Only matches in this status, e.g. FINISHED"
    ),
    current_user: User = Depends(get_current_user),
    uow: UnitOfWork = Depends(),
) -> PaginatedResponse[MatchResponse]:
    """A player's match history, newest first, in the same shape as your own."""
    async with uow:
        player, _ = await _visible_player(uow, current_user, player_id)
        matches, total = await uow.matches.get_matches_for_user(
            player.id, skip=(page - 1) * size, limit=size, status=match_status
        )
        items = [MatchResponse.model_validate(match) for match in matches]
        return PaginatedResponse.create(items=items, total=total, page=page, size=size)
