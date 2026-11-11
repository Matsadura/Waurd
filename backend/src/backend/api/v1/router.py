from backend.api.dependencies.auth import verify_csrf
from backend.api.v1.endpoints import auth, friendship, two_factor, users
from fastapi import APIRouter, Depends

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router)

# CSRF is applied per route: the login verification step has no session yet.
api_v1_router.include_router(two_factor.router)

api_v1_router.include_router(
    users.router,
    dependencies=[Depends(verify_csrf)],
)

api_v1_router.include_router(
    friendship.router,
    dependencies=[Depends(verify_csrf)],
)
