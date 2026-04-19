from typing import Literal

from pydantic import BaseModel, Field


class InsightTaskCreate(BaseModel):
    platform: str = Field(min_length=1, max_length=64)
    product_id: str = Field(min_length=1, max_length=256)
    analysis_provider_id: str | None = Field(default=None, max_length=128)
    dictionary_vertical_id: str = Field(
        default="general",
        min_length=1,
        max_length=64,
        description="词典类目：general 默认词典，electronics 电子产品等",
    )


InsightTaskStatus = Literal["pending", "running", "success", "failed", "cancelled"]


class InsightTaskPatch(BaseModel):
    status: InsightTaskStatus
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=4000)
    failure_stage: str | None = Field(default=None, max_length=128)


class TopicDiscoveryBody(BaseModel):
    """BERTopic 主题三池：需已分析成功且本机/子进程已安装 ml/requirements-topic-pools.txt。"""

    embedding_model: str = Field(
        default="ml/all-MiniLM-L6-v2",
        min_length=1,
        max_length=512,
        description="SentenceTransformer 目录（相对仓库根）或 Hub 名",
    )
    dry_run: bool = Field(default=False, description="仅打印摘要，不写 topic_pool_* 表")
