from backend.api.dependencies.auth import verify_csrf
from backend.api.v1.endpoints import auth, users
from fastapi import APIRouter, Depends

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router)

api_v1_router.include_router(
    users.router,
    # dependencies=[Depends(verify_csrf)],
)