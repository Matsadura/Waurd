from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Shared fields across user payload representations."""

    email: EmailStr = Field(..., description="The user's email address")


class UserCreateRequest(BaseModel):
    """Request payload for creating a new user."""

    model_config = ConfigDict(str_strip_whitespace=True)
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Unique username for the new user (3-32 characters)",
        example="new_user123",
    )
    email: EmailStr = Field(
        ...,
        description="Unique email address for the new user",
        example="user@example.com",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password for the new user (8-128 characters)",
        example="SecureP@ssw0rd!123",
    )


class UserResponse(UserBase):
    """Response payload for user data."""

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="Unique identifier for the user")
    username: str = Field(..., description="Username of the user", example="user123")
    created_at: datetime = Field(
        ...,
        description="Timestamp when the user was created",
        example="2023-01-01T12:00:00Z",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the user was last updated",
        example="2023-01-02T12:00:00Z",
    )
