from __future__ import annotations

# 与前端 menu.config 中 item.key 一致（系统设置用子项 key）
ALLOWED_MENU_KEYS: frozenset[str] = frozenset(
    {
        "insight",
        "pain-audit",
        "dictionary",
        "api-config",
        "audit-log",
        "account-permissions",
    }
)

# 任一为真则 API 层视为 admin（与 X-RSA-Role 对齐）
ADMIN_MENU_KEYS: frozenset[str] = frozenset(
    {"pain-audit", "dictionary", "api-config", "audit-log", "account-permissions"}
)


def derive_api_role(menu_keys: list[str]) -> str:
    ks = {k.strip() for k in menu_keys if isinstance(k, str) and k.strip()}
    if ks & ADMIN_MENU_KEYS:
        return "admin"
    if "insight" in ks:
        return "operator"
    return "readonly"


def normalize_menu_keys(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for k in raw:
        if not isinstance(k, str):
            continue
        s = k.strip()
        if s in ALLOWED_MENU_KEYS and s not in seen:
            seen.add(s)
            out.append(s)
    return out
