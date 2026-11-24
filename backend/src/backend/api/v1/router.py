from backend.api.dependencies.auth import verify_csrf
from backend.api.v1.endpoints import (
    admin,
    auth,
    chat,
    friendship,
    matchmaking,
    password,
    perks,
    two_factor,
    users,
)
from fastapi import APIRouter, Depends

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router)

# CSRF is applied per route: the login verification step has no session yet.
api_v1_router.include_router(two_factor.router)

# No CSRF: these routes take no session or cookie.
api_v1_router.include_router(password.router)

api_v1_router.include_router(
    users.router,
    dependencies=[Depends(verify_csrf)],
)

api_v1_router.include_router(
    friendship.router,
    dependencies=[Depends(verify_csrf)],
)

api_v1_router.include_router(
    matchmaking.router,
    dependencies=[Depends(verify_csrf)],
)

api_v1_router.include_router(
    perks.router,
    dependencies=[Depends(verify_csrf)],
)

api_v1_router.include_router(
    chat.router,
    dependencies=[Depends(verify_csrf)],
)

# Game master only: user management.
api_v1_router.include_router(
    admin.router,
    dependencies=[Depends(verify_csrf)],
)
