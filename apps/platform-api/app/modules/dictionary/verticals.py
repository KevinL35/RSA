from __future__ import annotations

from typing import TypedDict


class DictionaryVerticalMeta(TypedDict):
    id: str
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str


DICTIONARY_VERTICALS: tuple[DictionaryVerticalMeta, ...] = (
    {
        "id": "general",
        "label_zh": "默认词典",
        "label_en": "Default dictionary",
        "description_zh": "全类目基础词条；其他垂直会与其合并，专用词优先。",
        "description_en": "Baseline terms for all verticals; merged under category-specific overlays.",
    },
    {
        "id": "electronics",
        "label_zh": "电子产品",
        "label_en": "Electronics",
        "description_zh": "在默认词典上叠加电池、发热、屏幕、游戏场景等电子相关说法。",
        "description_en": "Adds battery, thermals, display, gaming usage on top of general seed.",
    },
)

VERTICAL_IDS: frozenset[str] = frozenset(v["id"] for v in DICTIONARY_VERTICALS)


def assert_valid_vertical_id(vid: str) -> str:
    s = (vid or "").strip()
    if not s:
        raise ValueError("dictionary_vertical_id 不能为空")
    if s not in VERTICAL_IDS:
        raise ValueError(f"无效 dictionary_vertical_id：{s!r}，允许：{', '.join(sorted(VERTICAL_IDS))}")
    return s
