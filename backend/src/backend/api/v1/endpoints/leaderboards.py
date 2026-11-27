from backend.api.dependencies.auth import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.leaderboard import LeaderboardRepository
from backend.schemas.leaderboard import LeaderboardFilter, LeaderboardResponse
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/leaderboards", tags=["Leaderboards"])


@router.get(
    "",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a paginated leaderboard",
)
async def get_leaderboard(
    filter_by: LeaderboardFilter = Query(
        LeaderboardFilter.ELO,
        description="elo, damage (lifetime), win_streak (best ever), heal (most "
        "HP one cast gave back) or words (highest-scoring casts)",
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> LeaderboardResponse:
    """Rank players by `filter_by`, highest first. Every board but `words` lists
    every player once; `words` lists single casts from finished matches."""
    repo = LeaderboardRepository(db)
    if filter_by == LeaderboardFilter.WORDS:
        items, total = await repo.get_words_leaderboard(limit=limit, offset=offset)
    else:
        items, total = await repo.get_player_leaderboard(
            filter_by, limit=limit, offset=offset
        )
    return LeaderboardResponse(
        filter_by=filter_by, items=items, total=total, limit=limit, offset=offset
    )
