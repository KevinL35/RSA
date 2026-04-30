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
        "id": "electronics",
        "label_zh": "电子产品",
        "label_en": "Electronics",
        "description_zh": "在默认词典上叠加电池、发热、屏幕、游戏场景等电子相关说法。",
        "description_en": "Electronics-oriented terms for battery, thermals, display and gaming usage.",
    },
    {
        "id": "furniture_kitchen",
        "label_zh": "家具厨房",
        "label_en": "Furniture & Kitchen",
        "description_zh": "家具与厨房场景词典，覆盖收纳、材质、安装、清洁、烹饪等表达。",
        "description_en": "Furniture and kitchen vertical terms for storage, materials, setup, cleaning and cooking.",
    },
    {
        "id": "fashion_shoes_bags",
        "label_zh": "服装鞋包",
        "label_en": "Fashion, Shoes & Bags",
        "description_zh": "服装鞋包场景词典，覆盖尺码、版型、材质、舒适度与穿搭表达。",
        "description_en": "Fashion, shoes and bags terms for sizing, fit, materials, comfort and styling.",
    },
)

VERTICAL_IDS: frozenset[str] = frozenset(v["id"] for v in DICTIONARY_VERTICALS)
DEFAULT_VERTICAL_ID: str = DICTIONARY_VERTICALS[0]["id"]


def assert_valid_vertical_id(vid: str) -> str:
    s = (vid or "").strip()
    if not s:
        raise ValueError("dictionary_vertical_id 不能为空")
    if s not in VERTICAL_IDS:
        raise ValueError(f"无效 dictionary_vertical_id：{s!r}，允许：{', '.join(sorted(VERTICAL_IDS))}")
    return s
