from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionCreate(BaseModel):
    title: str | None = None


class SessionUpdate(BaseModel):
    title: str


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)


class ChartData(BaseModel):
    columns: list[str] = []
    rows: list[list[Any]] = []


class ChatResponse(BaseModel):
    reply: str
    sql: str | None = None
    data: ChartData = Field(default_factory=ChartData)
    meta: dict[str, Any] = Field(default_factory=dict)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    meta: dict[str, Any] | None = None

    model_config = {"from_attributes": True}
