from backend.api.dependencies.auth import get_current_user
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.perks import PerkRepository
from backend.schemas.pagination import PaginatedResponse
from backend.schemas.perks import (
    AchievementResponse,
    PerkResponse,
    UpdateLoadoutRequest,
    UserAchievementResponse,
    UserLoadoutResponse,
)
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Perks, Deckbuilding & Achievements"])


@router.get(
    "/perks",
    response_model=PaginatedResponse[PerkResponse],
    status_code=status.HTTP_200_OK,
    summary="List all master game perks (modifiers, durability, target types).",
)
async def list_perks(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Perks per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> PaginatedResponse[PerkResponse]:
    """
    List paginated master game perks including their modifier types, durability,
    rarity, and target glyph types.
    """
    repo = PerkRepository(db)
    skip = (page - 1) * size
    perks, total = await repo.get_all_perks(skip=skip, limit=size)
    items = [PerkResponse.model_validate(p) for p in perks]
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/achievements",
    response_model=PaginatedResponse[AchievementResponse],
    status_code=status.HTTP_200_OK,
    summary="List all achievements, criteria, XP rewards, and associated perk unlocks.",
)
async def list_achievements(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Achievements per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> PaginatedResponse[AchievementResponse]:
    """
    List paginated game achievements with criteria thresholds, XP rewards,
    and associated perk unlocks.
    """
    repo = PerkRepository(db)
    skip = (page - 1) * size
    achievements, total = await repo.get_all_achievements(skip=skip, limit=size)
    items = [AchievementResponse.model_validate(a) for a in achievements]
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/users/me/achievements",
    response_model=list[UserAchievementResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user achievement progression (e.g., words cast toward 'Wild Wolf').",
)
async def get_my_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> list[UserAchievementResponse]:
    """
    Get the authenticated user's progress across all achievements,
    including completion status and percentage.
    """
    repo = PerkRepository(db)
    progress = await repo.get_user_achievements_progress(current_user.id)
    return [UserAchievementResponse.model_validate(p) for p in progress]


@router.get(
    "/users/me/loadout",
    response_model=UserLoadoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persistent starter perks unlocked from completed achievements.",
)
async def get_my_loadout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> UserLoadoutResponse:
    """
    Retrieve the player's active starter perk loadout and all perks
    they have unlocked and are eligible to equip.
    """
    repo = PerkRepository(db)
    loadout = await repo.get_user_loadout(current_user.id)
    return UserLoadoutResponse.model_validate(loadout)


@router.put(
    "/users/me/loadout",
    response_model=UserLoadoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Equip or configure active persistent starter perks before queuing.",
)
async def update_my_loadout(
    payload: UpdateLoadoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
) -> UserLoadoutResponse:
    """
    Equip active persistent starter perks for matches. Validates that every
    perk has been unlocked and the slot limit is respected.
    """
    repo = PerkRepository(db)
    updated_loadout = await repo.update_user_loadout(
        user_id=current_user.id,
        perk_ids=payload.perk_ids,
    )
    return UserLoadoutResponse.model_validate(updated_loadout)
