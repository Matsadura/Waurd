from backend.api.dependencies.auth import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.leaderboard import LeaderboardRepository
from backend.schemas.leaderboard import (
    DamageLeaderboardResponse,
    EloLeaderboardResponse,
    WordLeaderboardResponse,
)
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/leaderboards", tags=["Leaderboards"])


@router.get(
    "/elo",
    response_model=EloLeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated Elo leaderboard",
)
async def get_elo_leaderboard(
    limit: int = Query(20, ge=1, le=100, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> EloLeaderboardResponse:
    """
    Retrieve top players ranked by Elo rating in descending order,
    with deterministic tie-breaking on wins and user ID.
    """
    repo = LeaderboardRepository(db)
    items, total = await repo.get_elo_leaderboard(limit=limit, offset=offset)
    return EloLeaderboardResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/words",
    response_model=WordLeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated highest-scoring words leaderboard",
)
async def get_words_leaderboard(
    limit: int = Query(20, ge=1, le=100, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> WordLeaderboardResponse:
    """
    Retrieve top-scoring words cast across finished competitive matches
    ordered by damage dealt in descending order.
    """
    repo = LeaderboardRepository(db)
    items, total = await repo.get_words_leaderboard(limit=limit, offset=offset)
    return WordLeaderboardResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/damage",
    response_model=DamageLeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated lifetime damage leaderboard",
)
async def get_damage_leaderboard(
    limit: int = Query(20, ge=1, le=100, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> DamageLeaderboardResponse:
    """
    Retrieve players ranked by lifetime total damage dealt across matches
    in descending order.
    """
    repo = LeaderboardRepository(db)
    items, total = await repo.get_damage_leaderboard(limit=limit, offset=offset)
    return DamageLeaderboardResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
