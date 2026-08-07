from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, regex=r"^[A-Za-z0-9_.]+$")
    password: str = Field(..., min_length=8)
    confirm_password: str
    full_name: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ValidateResetTokenRequest(BaseModel):
    token: str = Field(min_length=32)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32)
    new_password: str = Field(..., min_length=8)
    confirm_password: str
