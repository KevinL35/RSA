from __future__ import annotations

from pydantic import BaseModel, Field

class CreateDictionaryReviewQueueBody(BaseModel):
    """人工新增主题：写入待审队列（与挖掘结果同源）。"""

    canonical: str = Field(min_length=2, max_length=512)
    synonyms: list[str] = Field(min_length=1, max_length=80)
    vertical_id: str | None = Field(default=None, max_length=64)


class DictionarySmartMergeRequest(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)
    queue_ids: list[str] = Field(min_length=1, max_length=120)


class DictionaryTaxonomyAgentReviewRequest(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)


class PatchReviewQueueBody(BaseModel):
    canonical: str = Field(min_length=2, max_length=512)
    synonyms: list[str] = Field(min_length=1, max_length=80)


class ApproveDictionaryEntryBody(BaseModel):
    """词典审核通过：写入各选中类目的 Supabase overlay（taxonomy_entries）。"""

    vertical_ids: list[str] = Field(min_length=1, max_length=16)
    dimension_6way: str = Field(min_length=1, max_length=64)
    canonical: str = Field(min_length=2, max_length=512)
    aliases: list[str] = Field(default_factory=list, max_length=80)
    batch_id: str | None = Field(default=None, max_length=128)
    source_topic_id: str | None = Field(default=None, max_length=128)
    review_queue_id: str | None = Field(
        default=None,
        max_length=64,
        description="对应 dictionary_review_queue.id，通过后标记为 approved",
    )


class RejectSynonymBody(BaseModel):
    vertical_id: str = Field(min_length=1, max_length=64)
    dimension_6way: str = Field(min_length=1, max_length=64)
    canonical: str = Field(min_length=1, max_length=512)
    alias: str = Field(min_length=1, max_length=512)
