import httpx

from backend.core.config import settings


async def get_database_credentials() -> dict:
    if not settings.VAULT_ROLE_ID or not settings.VAULT_SECRET_ID:
        raise RuntimeError("Vault AppRole credentials are missing")

    async with httpx.AsyncClient() as client:
        # Authenticate with Vault using AppRole
        response = await client.post(
            f"{settings.VAULT_ADDR}/v1/auth/approle/login",
            json={
                "role_id": settings.VAULT_ROLE_ID,
                "secret_id": settings.VAULT_SECRET_ID,
            },
        )
        response.raise_for_status()

        token = response.json()["auth"]["client_token"]

        # Read database credentials from KV v2
        response = await client.get(
            f"{settings.VAULT_ADDR}/v1/secret/data/waurd/database",
            headers={"X-Vault-Token": token},
        )
        response.raise_for_status()

        return response.json()["data"]["data"]
