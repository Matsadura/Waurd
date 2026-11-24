from uuid import UUID

from backend.api.dependencies.auth import get_current_user
from backend.core.exceptions import EntityNotFoundException, ForbiddenException
from backend.db.session import get_db
from backend.models.user import User
from backend.repositories.chat import ChatRepository
from backend.repositories.match import MatchRepository
from backend.schemas.chat import ChatMessageResponse, chat_message_response
from backend.schemas.pagination import PaginatedResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/chat", tags=["Chat"])


def page_of(messages, total: int, page: int, size: int):  # type: ignore[no-untyped-def]
    items = [chat_message_response(m, m.sender.username) for m in messages]
    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/global",
    response_model=PaginatedResponse[ChatMessageResponse],
    summary="Global chat history, newest first",
)
async def global_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Messages per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    messages, total = await ChatRepository(db).global_messages((page - 1) * size, size)
    return page_of(messages, total, page, size)


@router.get(
    "/direct/{user_id}",
    response_model=PaginatedResponse[ChatMessageResponse],
    summary="Direct messages with one player, newest first",
)
async def direct_history(
    user_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Messages per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    messages, total = await ChatRepository(db).direct_messages(
        current_user.id, user_id.bytes, (page - 1) * size, size
    )
    return page_of(messages, total, page, size)


@router.get(
    "/matches/{match_id}",
    response_model=PaginatedResponse[ChatMessageResponse],
    summary="A match's chat history, newest first (its players only)",
)
async def match_history(
    match_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Messages per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    match = await MatchRepository(db).get_match_by_id(match_id.bytes)
    if match is None:
        raise EntityNotFoundException("Match not found")
    if current_user.id not in (match.player1_id, match.player2_id):
        raise ForbiddenException("Only the match's players can read its chat")

    messages, total = await ChatRepository(db).match_messages(
        match_id.bytes, (page - 1) * size, size
    )
    return page_of(messages, total, page, size)
