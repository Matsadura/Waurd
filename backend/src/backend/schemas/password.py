from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PasswordForgotRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr = Field(..., description="Email address of the account")


class PasswordResetRequest(BaseModel):
    """The token from the reset link plus the new password."""

    model_config = ConfigDict(str_strip_whitespace=True)
    token: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Value of the token query parameter in the emailed link",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
    )


class PasswordForgotResponse(BaseModel):
    detail: str = "If an account with that email exists, a reset link is on its way."


class PasswordResetResponse(BaseModel):
    detail: str = "Password updated. Log in with your new password."
