from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PlatformLoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class PlatformLoginResponse(BaseModel):
    username: str
    role: str
    menu_keys: list[str]
    token: str


class PlatformUserCreateBody(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    menu_keys: list[str] = Field(default_factory=list)
    status: Literal["active", "disabled"] = "active"

    @field_validator("username")
    @classmethod
    def strip_username(cls, v: str) -> str:
        return v.strip()


class PlatformUserUpdateBody(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=1, max_length=256)
    menu_keys: list[str] | None = None
    status: Literal["active", "disabled"] | None = None

    @field_validator("username")
    @classmethod
    def strip_username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return v.strip()


class PlatformUserRow(BaseModel):
    id: str
    username: str
    status: str
    menu_keys: list[str]
    created_at: datetime

    @classmethod
    def from_record(cls, r: dict[str, Any]) -> "PlatformUserRow":
        mk = r.get("menu_keys")
        keys: list[str]
        if isinstance(mk, list):
            keys = [str(x) for x in mk]
        else:
            keys = []
        return cls(
            id=str(r["id"]),
            username=str(r["username"]),
            status=str(r["status"]),
            menu_keys=keys,
            created_at=r["created_at"],
        )


class PlatformUserListResponse(BaseModel):
    items: list[PlatformUserRow]
