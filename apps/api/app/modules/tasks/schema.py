from pydantic import BaseModel, Field


class InsightTaskCreate(BaseModel):
    platform: str = Field(min_length=1, max_length=64)
    product_id: str = Field(min_length=1, max_length=256)
    analysis_provider_id: str | None = Field(default=None, max_length=128)
