from __future__ import annotations

import uuid
from typing import Any

import bcrypt
from supabase import Client

from .constants import normalize_menu_keys
from .schemas import PlatformUserRow


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def list_users(sb: Client) -> list[PlatformUserRow]:
    res = (
        sb.table("platform_users")
        .select("id, username, status, menu_keys, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    rows = res.data or []
    return [PlatformUserRow.from_record(r) for r in rows]


def get_by_username(sb: Client, username: str) -> dict[str, Any] | None:
    u = username.strip()
    if not u:
        return None
    res = sb.table("platform_users").select("*").eq("username", u).limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def get_by_id(sb: Client, user_id: str) -> dict[str, Any] | None:
    res = sb.table("platform_users").select("*").eq("id", user_id).limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def create_user(
    sb: Client,
    *,
    username: str,
    password: str,
    menu_keys: list[str],
    status: str,
) -> PlatformUserRow:
    keys = normalize_menu_keys(menu_keys)
    row = {
        "username": username.strip(),
        "password_hash": hash_password(password),
        "status": status,
        "menu_keys": keys,
    }
    sb.table("platform_users").insert(row).execute()
    sel = (
        sb.table("platform_users")
        .select("id, username, status, menu_keys, created_at")
        .eq("username", row["username"])
        .limit(1)
        .execute()
    )
    data = sel.data or []
    if not data:
        raise RuntimeError("insert platform_user returned no row")
    return PlatformUserRow.from_record(data[0])


def update_user(
    sb: Client,
    user_id: str,
    *,
    username: str | None = None,
    password: str | None = None,
    menu_keys: list[str] | None = None,
    status: str | None = None,
) -> PlatformUserRow | None:
    existing = get_by_id(sb, user_id)
    if not existing:
        return None
    patch: dict[str, Any] = {}
    if username is not None:
        patch["username"] = username.strip()
    if password is not None:
        patch["password_hash"] = hash_password(password)
    if menu_keys is not None:
        patch["menu_keys"] = normalize_menu_keys(menu_keys)
    if status is not None:
        patch["status"] = status
    if not patch:
        return PlatformUserRow.from_record(
            {
                "id": existing["id"],
                "username": existing["username"],
                "status": existing["status"],
                "menu_keys": existing.get("menu_keys") or [],
                "created_at": existing["created_at"],
            }
        )
    sb.table("platform_users").update(patch).eq("id", user_id).execute()
    refreshed = get_by_id(sb, user_id)
    if not refreshed:
        return None
    return PlatformUserRow.from_record(
        {
            "id": refreshed["id"],
            "username": refreshed["username"],
            "status": refreshed["status"],
            "menu_keys": refreshed.get("menu_keys") or [],
            "created_at": refreshed["created_at"],
        }
    )


def delete_user(sb: Client, user_id: str) -> bool:
    if get_by_id(sb, user_id) is None:
        return False
    sb.table("platform_users").delete().eq("id", user_id).execute()
    return get_by_id(sb, user_id) is None


def try_login(sb: Client, username: str, password: str) -> tuple[PlatformUserRow, str] | None:
    rec = get_by_username(sb, username)
    if not rec:
        return None
    if rec.get("status") != "active":
        return None
    ph = rec.get("password_hash")
    if not isinstance(ph, str) or not verify_password(password, ph):
        return None
    mk = rec.get("menu_keys")
    keys = normalize_menu_keys(list(mk) if isinstance(mk, list) else [])
    row = PlatformUserRow.from_record(
        {
            "id": rec["id"],
            "username": rec["username"],
            "status": rec["status"],
            "menu_keys": keys,
            "created_at": rec["created_at"],
        }
    )
    token = f"pu_{uuid.uuid4().hex}"
    return row, token
