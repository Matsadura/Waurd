from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Request payload for user login."""

    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr = Field(
        ...,
        description="Email address of the user",
        example="user@example.com",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password of the user (8-128 characters)",
        example="SecureP@ssw0rd!123",
    )


class LogoutRequest(BaseModel):
    """Request payload for user logout."""

    user_id: int = Field(..., description="ID of the user to log out", example=1)
    username: str = Field(
        ..., description="Username of the user to log out", example="user123"
    )
