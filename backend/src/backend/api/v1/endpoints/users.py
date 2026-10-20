from backend.api.dependencies.auth import get_current_user, get_session_store
from backend.core.security import hash_password
from backend.core.session_store import RedisSessionStore
from backend.db.uow import UnitOfWork
from backend.schemas.user import UserCreateRequest, UserResponse
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["Users"])

# @router.post("/register", response_model=UserResponse)
# async def register_user(
#     user_create: UserCreateRequest,
#     current_user: UserResponse = Depends(get_current_user),
# ) -> UserResponse:
#     """Register a new user"""
#     async with UnitOfWork() as uow:
#         existing_user = await uow.users.get_by_email(user_create.email)
#         if existing_user:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Email already registered.",
#             )

#         hashed_password = hash_password(user_create.password)
#         new_user = await uow.users.create(
#             username=user_create.username,
#             email=user_create.email,
#             hashed_password=hashed_password,
#         )
#         await uow.commit()

#     return UserResponse.model_validate(new_user)