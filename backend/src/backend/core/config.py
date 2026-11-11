# backend/core/config.py
import os

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "FastAPI MySQL Service"
    API_V1_STR: str = "/api/v1"

    # MySQL Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "app_user"
    DB_PASSWORD: str = "app_password"
    DB_NAME: str = "app_db"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 20
    REDIS_URL: str = (
        os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    )  # Default value; will be overridden by computed property

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    # GOOGLE_FRONTEND_REDIRECT_URI: str = "http://localhost:3000"
    GOOGLE_FRONTEND_REDIRECT_URI: str = "http://localhost:8000/docs"  # For testing purposes; replace with your frontend URL in production
    GOOGLE_OAUTH_STATE_TTL_SECONDS: int = 600

    # Two-factor authentication (emailed codes)
    TWO_FACTOR_COOKIE_NAME: str = "two_factor_token"
    TWO_FACTOR_CODE_TTL_SECONDS: int = 600
    TWO_FACTOR_MAX_ATTEMPTS: int = 5
    TWO_FACTOR_RESEND_COOLDOWN_SECONDS: int = 60

    # Password reset links point at this frontend page, which reads ?token=
    PASSWORD_RESET_URL: str = "http://localhost:5173/reset-password"
    PASSWORD_RESET_TTL_SECONDS: int = 1800
    PASSWORD_RESET_COOLDOWN_SECONDS: int = 60

    # Outgoing email. Defaults suit Gmail; MAIL_PASSWORD must be a Google app
    # password, not the account password.
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: SecretStr | None = None
    MAIL_FROM: str | None = None  # Defaults to MAIL_USERNAME
    MAIL_FROM_NAME: str = "Waurd"
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # @computed_field
    # @property
    # def REDIS_URL(self) -> str:
    #     auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
    #     return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Cookie & Session Security
    SESSION_COOKIE_NAME: str = "session_id"
    CSRF_COOKIE_NAME: str = "csrf_token"
    COOKIE_SECURE: bool = False  # Set to True in production (HTTPS)
    SESSION_TTL_SECONDS: int = 86400 * 7  # 7 days
    SESSION_COOKIE_SAMESITE: str = "lax"  # Options: 'strict', 'lax', 'none'

    # CORS (Must specify exact origins when allow_credentials=True)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
