import uuid
from typing import Optional

from pydantic import BaseModel


class StyleFeature(BaseModel):
    label: str
    confidence: float
    examples: list[str]


class StyleProfile(BaseModel):
    id: Optional[uuid.UUID] = None
    board_ids: list[str]
    anchor_pin_urls: list[str] = []
    style_context_path: Optional[str] = None
    features: list[StyleFeature] = []


class UserPreferences(BaseModel):
    sizes: list[str] = []
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    brand_allowlist: list[str] = []
    brand_blocklist: list[str] = []


class Listing(BaseModel):
    id: str
    title: str
    price: float
    brand: Optional[str] = None
    size: Optional[str] = None
    image_urls: list[str] = []
    vinted_url: str
    score: Optional[float] = None
    reasoning: Optional[str] = None
    feedback: Optional[str] = None  # "liked" | "disliked"
