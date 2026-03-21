from typing import Literal

from pydantic import BaseModel, Field


class InsightTaskCreate(BaseModel):
    platform: str = Field(min_length=1, max_length=64)
    product_id: str = Field(min_length=1, max_length=256)
    analysis_provider_id: str | None = Field(default=None, max_length=128)


InsightTaskStatus = Literal["pending", "running", "success", "failed", "cancelled"]


class InsightTaskPatch(BaseModel):
    status: InsightTaskStatus
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=4000)
    failure_stage: str | None = Field(default=None, max_length=128)
