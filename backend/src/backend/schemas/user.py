from datetime import datetime

from backend.core.identifiers import user_id_to_string
from backend.schemas.match import MatchResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    avatar_url: str | None = Field(
        None,
        description="Optional URL for the user's avatar image",
        example="https://example.com/avatar.png",
    )


class UserResponse(UserBase):
    """Response payload for user data."""

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="Unique identifier for the user")
    email: EmailStr = Field(..., description="Email address of the user")
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
    avatar_url: str | None = Field(
        None,
        description="URL for the user's avatar image",
        example="https://example.com/avatar.png",
    )

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id(cls, value: bytes | str) -> str:
        return user_id_to_string(value)


class UserStatsResponse(BaseModel):
    """Response payload for user statistics."""

    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="Unique identifier for the user")
    matches_played: int = Field(..., description="Total number of matches played")
    wins: int = Field(..., description="Total number of wins")
    losses: int = Field(..., description="Total number of losses")
    draws: int = Field(..., description="Total number of draws")
    rating_elo: int = Field(..., description="Current ELO rating of the user")
    highest_scoring_word: str | None = Field(
        None,
        description="The highest scoring word played by the user",
        example="QUIZZIFY",
    )
    highest_word_score: int = Field(
        ...,
        description="The score of the highest scoring word played by the user",
        example=100,
    )
    total_damage_dealt: int = Field(
        ...,
        description="Total damage dealt by the user across all matches",
        example=5000,
    )

    @field_validator("user_id", mode="before")
    @classmethod
    def serialize_user_id(cls, value: bytes | str) -> str:
        return user_id_to_string(value)


class UserMatchesResponse(BaseModel):
    """Response payload for user matches."""

    model_config = ConfigDict(from_attributes=True)
    matches: list["MatchResponse"] = Field(
        ...,
        description="List of matches associated with the user",
    )
