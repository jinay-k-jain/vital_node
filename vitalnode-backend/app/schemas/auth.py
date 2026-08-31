"""
Auth schemas - matching the frontend User type exactly.
Frontend User: { id, name, role, staffId, department }
"""
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class LoginRequest(BaseModel):
    staff_id: str = Field(..., min_length=1, max_length=50, description="Staff ID (e.g. TN-0421)")
    password: str = Field(..., min_length=1, description="Password")

    model_config = {"json_schema_extra": {"example": {"staff_id": "TN-0421", "password": "demo123"}}}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """
    Matches the frontend User type exactly:
    { id, name, role, staffId, department }
    """
    id: str  # UUID as string (matches frontend string id)
    name: str
    role: str  # "Triage Nurse" | "Clinician" | "Administrator"
    staff_id: str = Field(alias="staffId")
    department: str

    model_config = {"populate_by_name": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
