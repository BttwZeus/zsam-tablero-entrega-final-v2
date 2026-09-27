from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str


class BoardCreate(BaseModel):
    name: str


class BoardOut(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class CardCreate(BaseModel):
    title: str
    description: str = ""
    assignee_email: str = ""
    due_date: Optional[datetime] = None


class CardUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_email: Optional[str] = None
    due_date: Optional[datetime] = None


class PlantillaExportRequest(BaseModel):
    usuario_id: str


class CardOut(BaseModel):
    id: str
    board_id: str
    title: str
    description: str
    status: str
    assignee_email: str
    due_date: Optional[datetime]
    attachment_key: Optional[str]

    class Config:
        from_attributes = True
