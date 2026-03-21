"""TB-10：对比前置条件不满足时的可读提示与引导文案。"""

from __future__ import annotations

from typing import Any


def format_compare_prerequisite_error(raw: dict[str, Any]) -> dict[str, Any]:
    """
    将 build_product_compare 的 _missing 载荷格式化为 HTTP 400 detail（FastAPI 会包在 response.detail 下）。
    """
    reasons: dict[str, str | None] = raw["reasons"]
    products: dict[str, Any] = raw["products"]
    zh_lines: list[str] = []
    en_lines: list[str] = []
    for side, label_zh, label_en in (
        ("a", "商品 A", "Product A"),
        ("b", "商品 B", "Product B"),
    ):
        r = reasons.get(side)
        if not r:
            continue
        p = products[side]
        pid = f"{p['platform']}/{p['product_id']}"
        if r == "no_success_task":
            zh_lines.append(
                f"{label_zh}（{pid}）尚无「成功」状态的洞察任务；"
                "请先在「洞察分析」添加商品并完成拉取评论与分析。"
            )
            en_lines.append(
                f"{label_en} ({pid}) has no successful insight task. "
                "In Insight analysis, add the product, fetch reviews, then run analysis."
            )
        elif r == "empty_analysis":
            tid = p.get("insight_task_id") or ""
            zh_lines.append(
                f"{label_zh}（{pid}）的洞察任务已标记成功，但未落库评论分析结果（任务 {tid}）；"
                "请重试「分析」或检查分析服务配置。"
            )
            en_lines.append(
                f"{label_en} ({pid}) has a successful task but no stored review analysis "
                f"(task {tid}). Retry Analyze or check the analysis provider."
            )

    guidance_zh = (
        "建议：前往「洞察分析」→ 添加商品 → 拉取评论 → 执行分析；"
        "两侧商品均具备可对比的分析数据后再回到本页。"
    )
    guidance_en = (
        "Suggested: Insight analysis → add product → fetch reviews → analyze; "
        "return here when both products have comparable stored analysis."
    )

    missing = {
        "a": reasons.get("a") is not None,
        "b": reasons.get("b") is not None,
    }

    summary_en = " ".join(en_lines) if en_lines else guidance_en

    return {
        "code": "MISSING_INSIGHT_DATA",
        "message": summary_en,
        "messages": {
            "zh_CN": "\n".join(zh_lines) if zh_lines else guidance_zh,
            "en": "\n".join(en_lines) if en_lines else guidance_en,
        },
        "guidance": {"zh_CN": guidance_zh, "en": guidance_en},
        "next_step": {
            "route": "/insight-analysis",
            "label_zh": "打开洞察分析",
            "label_en": "Open Insight analysis",
        },
        "missing": missing,
        "reasons": reasons,
        "products": products,
    }
