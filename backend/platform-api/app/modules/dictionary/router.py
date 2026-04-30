from __future__ import annotations

from fastapi import APIRouter

from .review_queue_router import router as review_queue_router
from .taxonomy_router import router as taxonomy_router

router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])
router.include_router(review_queue_router)
router.include_router(taxonomy_router)
