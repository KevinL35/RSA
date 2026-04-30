"""
DeepSeek ↔ RSA platform-api 的 TB-3 协议适配层。

运行：
  cd backend/deepseek-adapter && pip install -r requirements.txt
  export DEEPSEEK_API_KEY=sk-... && uvicorn main:app --host 0.0.0.0 --port 9100

platform-api .env：
  ANALYSIS_PROVIDER_URL=http://127.0.0.1:9100/analyze
  ANALYSIS_PROVIDER_API_KEY=<与 ADAPTER_SHARED_SECRET 相同，若配置了的话>

Agent 补洞（可选，同一进程）：
  AGENT_ENRICHMENT_URL=http://127.0.0.1:9100/agent-enrich

词典智能合并（platform-api 主题挖掘 / 智能体审核）：
  POST /dictionary-smart-merge  （platform-api 默认 DEEPSEEK_ADAPTER_DICTIONARY_SMART_MERGE_URL）

洞察摘要（可选，同一进程）：
  INSIGHT_SUMMARY_URL=http://127.0.0.1:9100/insight-summary
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request  # pyright: ignore[reportMissingImports]
from openai import OpenAI  # pyright: ignore[reportMissingImports]
from pydantic_settings import BaseSettings, SettingsConfigDict  # pyright: ignore[reportMissingImports]

app = FastAPI(title="RSA DeepSeek TB-3 Adapter", version="0.1.0")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-reasoner"
    # 摘要任务（/insight-summary）专用模型；默认 deepseek-chat
    # 摘要场景不需要思维链。可在 .env 单独覆盖 DEEPSEEK_SUMMARY_MODEL=deepseek-reasoner 强制走推理模型。
    deepseek_summary_model: str = "deepseek-chat"
    # 词典智能合并：结构化 JSON，默认用 chat 避免 reasoner 输出夹杂思维链
    deepseek_dictionary_merge_model: str = "deepseek-chat"
    deepseek_summary_request_timeout: float = 90.0
    deepseek_max_reviews_per_call: int = 25
    adapter_shared_secret: str = ""
    adapter_host: str = "0.0.0.0"
    adapter_port: int = 9100


def get_settings() -> Settings:
    return Settings()


DICTIONARY_SMART_MERGE_SYSTEM = """你是电商评论挖掘与词典治理专家。用户会给出 JSON：词典类目、六维维度、以及多条待审词条（每条含 queue_id、canonical 关键词、synonyms 同义词数组）。

输入中除 `items` 外，还可能有 `existing_dictionary_entries`：该「词典 vertical + 六维 dimension」下**已正式收录**的词条（只读背景，用于去重、消歧、避免与同义词表冲突）。你**不得**对 `existing_dictionary_entries` 输出任何修改指令；只能利用它们来更好地规划对 `items` 的合并、删同义词与驳回。

你的任务：
1) 判断哪些词条适合进入该「词典 + 六维」正式收录；不适合的应标记为驳回（退回主题挖掘人工区，类型为已驳回）。
2) 对适合收录的词条：可合并语义重复的多条关键词为一条（选一个更代表性的 canonical），去掉不自然、易歧义、或与该维度无关的同义词；若与 `existing_dictionary_entries` 中某条 canonical 或别名高度重复，应优先合并进更干净的一条或予以驳回并简述理由。
3) 输出必须是**单个 JSON 对象**，不要 Markdown，不要解释性文字。键名固定如下：

{
  "updates": [ { "queue_id": "<uuid>", "canonical": "...", "synonyms": ["..."] } ],
  "rejects": [ { "queue_id": "<uuid>", "reason_zh": "一句话" } ],
  "merge_groups": [
    {
      "keep_queue_id": "<uuid>",
      "drop_queue_ids": ["<uuid>"],
      "canonical": "...",
      "synonyms": ["..."]
    }
  ]
}

硬性规则：
- 输入里出现的每个 queue_id 必须**恰好出现一次**：要么出现在某条 merge_groups 的 keep_queue_id 或 drop_queue_ids 里，要么出现在 updates 单独一行，要么出现在 rejects 里。不要遗漏、不要重复。
- updates / merge_groups 里 synonyms 至少含 1 个字符串；不要输出空数组。
- merge_groups：合并后只保留 keep_queue_id 对应行，语义上吸收 drop_queue_ids 的词条；canonical/synonyms 为合并后的结果。
- rejects：表示不应收录进该词典该维度（用户会将其标为已驳回并回到主题挖掘列表）。
- 尽量保留用户语言（中文/英文）与产品术语，不要随意翻译成无关词。
"""


INSIGHT_SUMMARY_SYSTEM = """你是一名资深电商商品分析师，正在为品牌 / 运营团队撰写简报。
你的任务是：(1) 总结这款商品的优势；(2) 总结商品痛点；(3) 把这些信号转成可落地的优化空间。

语言（强制，不可妥协）：
- 必须始终使用清晰、专业的简体中文回答。
- 即使输入的 JSON、证据原话、关键词或商品标题是英文 / 日文 / 西班牙文 / 其它任何语言，
  也必须仅输出中文。
- 引用关键词或原话时，先把它翻译成自然的中文表达再使用，不要在回答里保留原文字符，
  也不要写「(意为...)」「翻译自...」这类注脚。
- 如果你不小心用了其它语言开头，请停下并整段用中文重写。

输入（用户消息）：
一份 JSON，包含商品上下文（product_id、platform、product_snapshot.title / price_display / image_url）
以及聚合的评论归因（top_keywords_by_dimension、sample_evidence_quotes 等）。
top_keywords_by_dimension 是一个 JSON 对象，键为六维之一：pros, cons, return_reasons,
purchase_motivation, user_expectation, usage_scenario；每个键对应一个数组，元素为 {keyword, count}，
按本维度内部命中行数降序，最多 5 条。同一关键词可能同时出现在多个维度（口径互相独立）。
六个维度的键名为：pros, cons, return_reasons, purchase_motivation, user_expectation, usage_scenario。

输出格式（严格遵守）：
请按下列四个小节标题，按此顺序输出，纯文本。
每个小节内的要点必须使用阿拉伯数字加中文顿号编号：1、2、3、4、5。

格式禁令（必须全部满足）：
1、禁止使用任何 Markdown 语法，绝对不要出现星号、井号、反引号、下划线，或两个连续星号这种加粗写法。
2、禁止在正文里使用任何形式的括号，包括圆括号、方括号、花括号、中文括号「（）」「【）」「《》」。
   需要补充说明时直接写在句子里。
3、禁止使用减号或破折号作为列表符号或行首符号。需要分隔时改用中文逗号或句号。
4、不要使用引号包裹关键词，直接写裸词即可。
5、每个要点占一行，行首仅用「数字+顿号」开头，例如「1、…」。
6、严禁出现以下话术：「提及 X 次」「出现 X 次」「该维度下提及」「N 条相关提及」「频次」「计数」
   或任何「X 次」「X 条」表述（除「商品概要」固定那两句话里的评论数 X / Y 之外）。
   你可以在心里把关键词作为依据，但写出来时只描述现象与影响，绝不输出原始计数或原文 keyword 字符串。
7、严禁出现内部字段名，例如：top_keywords_by_dimension、sample_evidence_quotes、pros、cons、
   return_reasons、purchase_motivation、user_expectation、usage_scenario、dictionary_vertical_id 等；
   也不要出现「关键词」「维度」「样本」「证据」「JSON」这类元数据用词。

商品概要
1、本节只输出一段连续文字，不分多行，不编号，不要使用「1、」开头，不要写「商品：」「售价：」「评论概况：」这类前缀。
2、内容由两部分用中文句号自然连接成一段：
   第一部分：用一两句话直接描述这款商品，覆盖关键卖点、目标用户、典型使用场景；不要重复 ASIN 或售价。
   第二部分：固定写「本轮评论洞察共有 X 条评论，其中 Y 条命中六维归因。」
              X 取自 review_total_count；Y 取自 matched_review_count；任一缺失就写「未知」。
3、示例：
   这是一款一万毫安时的太阳能充电宝，带有无线充电和 20 瓦快充功能，并配有双头手电筒，主要面向露营、徒步等户外活动爱好者以及日常通勤需要备用电源的用户。本轮评论洞察共有 100 条评论，其中 72 条命中六维归因。
4、本节绝对不要出现售价、ASIN、product_id 等任何字段原值或字段名。
5、本节不得出现任何括号、星号、井号、引号、列表符号或行首数字。

商品优势
1、列 3 到 5 条。每条用一句完整的中文，自然描述用户最满意的那一面，并解释为什么这点对目标用户有意义。
2、用日常运营语言写，例如「便携性出色，单手操作适合通勤与差旅」；不要出现关键词原文、计数、维度名等元数据。
3、要点之间互不重复，覆盖不同的卖点角度。

商品痛点
1、列 3 到 5 条，反映用户实际抱怨与导致退货的核心问题。
2、每条用一句话写出问题本身加上对用户的影响，例如「按键回弹不稳，长时间使用容易误触并打断操作」。
3、不要写次数，也不要出现关键词原文、字段名或元数据。

优化空间
1、列 3 到 5 条按优先级排序、具体且可执行的建议，覆盖产品、包装、详情页文案、运营、QA 等。
2、每条必须自然挂回上面某个痛点或未满足期望，写明做什么改动以及预期能解决哪种用户问题。
3、优先给团队真的能落地的动作：设计微调、文案更新、QA 抽检、FAQ、包装、附赠配件、说明书改版等。
4、禁止使用「提升品质」「优化体验」这类空话；也不要出现次数、关键词原文或字段名。

事实约束（仅供你心里参考，不要写到正文）：
1、商品优势只参考 top_keywords_by_dimension.pros 与 purchase_motivation；
   商品痛点只参考 top_keywords_by_dimension.cons 与 return_reasons；
   优化空间以痛点为主，可参考 user_expectation 与 usage_scenario 找到落差。
2、不要编造任何数字、品牌、功能或竞品，输入里没有的就不要说。
3、如果某一节信号太少，用一句话自然地说明用户对该方面反馈较少，不要写具体次数。

风格：客观、自然、决策导向，像分析师在向运营口头汇报，不堆术语，不引用关键词原文，不暴露任何字段。
引用商品时优先使用 product_snapshot.title，没有时再用 ASIN。
整体长度约 350 到 550 个中文字。
"""


SYSTEM_PROMPT = """You are an e-commerce review analyst. For each review, output structured JSON only.

Rules:
- sentiment.label must be one of: negative, neutral, positive. Include confidence 0-1 if possible.
- dimensions: array of hits from these six keys ONLY: pros, cons, return_reasons, purchase_motivation, user_expectation, usage_scenario.
- Each dimension object: dimension (string), keywords (array of short English phrases, 1-3 words each), evidence_quote (short excerpt from the review text, same language as review), highlight_spans optional (start/end UTF-16 or byte-agnostic offsets are not required — use [] if unsure).
- Use only dimensions that truly apply; omit empty dimensions or use empty keywords [] if none.
- Output MUST be a single JSON object with key "reviews" whose value is an array aligned to the input review ids in order.
- Each element: {"review_id": "<uuid>", "sentiment": {"label": "...", "confidence": 0.0}, "dimensions": [...]}

No markdown fences. No commentary outside JSON."""


def _auth_ok(authorization: str | None, secret: str) -> bool:
    if not (secret or "").strip():
        return True
    exp = f"Bearer {secret.strip()}"
    return (authorization or "").strip() == exp


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("top level not object")
    return obj


def _call_deepseek_batch(
    client: OpenAI,
    model: str,
    batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lines = []
    for r in batch:
        rid = r.get("id")
        title = (r.get("title") or "").strip()
        body = (r.get("raw_text") or "").strip()
        rating = r.get("rating")
        lines.append(
            json.dumps(
                {"review_id": str(rid), "title": title, "rating": rating, "text": body[:8000]},
                ensure_ascii=False,
            )
        )
    user_content = (
        "Analyze these reviews (JSON lines, one review per line).\n"
        + "\n".join(lines)
        + '\n\nReturn JSON: {"reviews":[...]} with the same review_id values and in the same order.'
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    msg = resp.choices[0].message.content
    if not msg:
        raise ValueError("empty model response")
    payload = _extract_json_object(msg)
    raw_list = payload.get("reviews")
    if not isinstance(raw_list, list):
        raise ValueError("missing reviews array")
    return [x for x in raw_list if isinstance(x, dict)]


def _run_tb3_body(body: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    s = get_settings()
    if not (s.deepseek_api_key or "").strip():
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY not set")
    if not _auth_ok(authorization, s.adapter_shared_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")

    reviews = body.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return {"reviews": []}

    client = OpenAI(
        api_key=s.deepseek_api_key.strip(),
        base_url=s.deepseek_base_url.strip().rstrip("/"),
    )
    model = s.deepseek_model.strip() or "deepseek-reasoner"
    chunk = max(1, min(50, int(s.deepseek_max_reviews_per_call or 25)))

    out_items: list[dict[str, Any]] = []
    for i in range(0, len(reviews), chunk):
        batch = reviews[i : i + chunk]
        if not all(isinstance(x, dict) for x in batch):
            continue
        part = _call_deepseek_batch(client, model, batch)
        # align by review_id from batch
        by_id = {str(x.get("review_id") or x.get("id") or ""): x for x in part}
        for r in batch:
            rid = str(r.get("id", ""))
            item = by_id.get(rid)
            if item:
                item.setdefault("review_id", rid)
                out_items.append(item)
            else:
                out_items.append(
                    {
                        "review_id": rid,
                        "sentiment": {"label": "neutral", "confidence": None},
                        "dimensions": [],
                    }
                )

    return {"reviews": out_items, "_adapter": "deepseek", "_model": model}


def _call_dictionary_smart_merge(
    client: OpenAI,
    model: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    user_content = (
        "请严格按 system 要求只输出 JSON 对象，不要其它文字。\n\n输入：\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DICTIONARY_SMART_MERGE_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.15,
    )
    msg = resp.choices[0].message.content
    if not msg:
        raise ValueError("empty model response")
    return _extract_json_object(msg)


@app.post("/dictionary-smart-merge")
async def dictionary_smart_merge(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """词典智能合并：输入多条 queue 词条 JSON，返回 updates / rejects / merge_groups。"""
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {e!s}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be object")
    s = get_settings()
    if not (s.deepseek_api_key or "").strip():
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY not set")
    if not _auth_ok(authorization, s.adapter_shared_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    client = OpenAI(
        api_key=s.deepseek_api_key.strip(),
        base_url=s.deepseek_base_url.strip().rstrip("/"),
    )
    model = (s.deepseek_dictionary_merge_model or "").strip() or "deepseek-chat"
    try:
        plan = _call_dictionary_smart_merge(client, model, body)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"dictionary smart merge failed: {e!s}") from e
    return {"plan": plan, "_adapter": "deepseek", "_model": model}


def _call_deepseek_insight_summary(
    client: OpenAI,
    model: str,
    context: dict[str, Any],
    *,
    timeout: float,
) -> str:
    user_content = (
        "请严格使用简体中文回答，整篇文风自然、客观、像运营分析师在口头汇报，不要暴露任何内部字段名、关键词原文或计数。"
        "引用任何非中文的关键词或原话时，先翻译成自然的中文表达再使用，并只把它当作隐含的判断依据，不要把原词写进正文。"
        "整篇严禁出现「提及 X 次」「出现 X 次」「N 条相关提及」「频次」「计数」之类计数措辞，也不要写「关键词」「维度」「样本」「JSON」「字段」等元数据用词。"
        "全篇禁止出现星号、双星号、井号、反引号、任何形式的括号（圆括号、方括号、花括号、中文「（）」「【】」「《》」），"
        "禁止用减号或破折号作为列表符号；要列要点时，仅使用「1、」「2、」「3、」这种阿拉伯数字加顿号开头。"
        "下方 JSON 是结构化输入，仅供你心里依据，不要在正文里复述其字段：\n\n"
        + json.dumps(context, ensure_ascii=False)
    )
    resp = client.with_options(timeout=timeout).chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": INSIGHT_SUMMARY_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    msg = resp.choices[0].message.content
    if not msg:
        raise ValueError("empty model response")
    return msg.strip()


@app.post("/insight-summary")
async def insight_summary(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """platform-api 传入 context JSON，返回 { summary, model }。"""
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {e!s}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be object")
    s = get_settings()
    if not (s.deepseek_api_key or "").strip():
        raise HTTPException(status_code=503, detail="DEEPSEEK_API_KEY not set")
    if not _auth_ok(authorization, s.adapter_shared_secret):
        raise HTTPException(status_code=401, detail="Unauthorized")
    context = body.get("context")
    if not isinstance(context, dict):
        raise HTTPException(status_code=400, detail="body.context must be an object")
    client = OpenAI(
        api_key=s.deepseek_api_key.strip(),
        base_url=s.deepseek_base_url.strip().rstrip("/"),
    )
    # 摘要走专用模型（默认 deepseek-chat），避免 reasoner 长思维链导致 platform-api 120s 超时；
    # 实在想用 reasoner，把 .env 里 DEEPSEEK_SUMMARY_MODEL 改成 deepseek-reasoner 即可。
    model = (s.deepseek_summary_model or "").strip() or "deepseek-chat"
    timeout = float(s.deepseek_summary_request_timeout or 90.0)
    text = _call_deepseek_insight_summary(client, model, context, timeout=timeout)
    return {"summary": text, "model": model, "_adapter": "deepseek"}


@app.post("/analyze")
async def analyze(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """与 platform-api TB-3 分析源相同请求体。"""
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {e!s}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be object")
    return _run_tb3_body(body, authorization)


@app.post("/agent-enrich")
async def agent_enrich(request: Request, authorization: str | None = Header(default=None)) -> dict:
    """与 platform-api Agent 增强相同请求体（子集 reviews + enrichment_mode）。"""
    try:
        body = await request.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"invalid json: {e!s}") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="body must be object")
    return _run_tb3_body(body, authorization)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
