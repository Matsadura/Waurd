from backend.core.two_factor import TwoFactorAction
from pydantic import BaseModel, Field, field_validator


class TwoFactorCodeRequest(BaseModel):
    """A 6-digit code from the verification email."""

    code: str = Field(
        ...,
        pattern=r"^\d{6}$",
        description="6-digit code from the verification email",
    )

    @field_validator("code", mode="before")
    @classmethod
    def strip_spaces(cls, value: object) -> object:
        # People often copy codes as "123 456" or with stray spaces.
        return value.replace(" ", "") if isinstance(value, str) else value


class TwoFactorCodeSendRequest(BaseModel):
    action: TwoFactorAction = Field(
        ..., description="Whether the code will turn 2FA on or off"
    )


class TwoFactorStatusResponse(BaseModel):
    enabled: bool = Field(..., description="Whether 2FA is enabled for the user")


class TwoFactorCodeSentResponse(BaseModel):
    detail: str = "Verification code sent"
    email_hint: str = Field(..., description="Masked address the code went to")


class TwoFactorChallengeResponse(BaseModel):
    """Returned by login when an emailed code is still required."""

    detail: str = "Two-factor authentication required"
    two_factor_required: bool = True
    email_hint: str = Field(..., description="Masked address the code went to")
