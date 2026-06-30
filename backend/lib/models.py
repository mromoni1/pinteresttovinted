import uuid
from datetime import datetime
from enum import IntEnum
from typing import Annotated, Optional

from pydantic import BaseModel, Field


class FeedbackRating(IntEnum):
    one = 1
    two = 2
    three = 3
    four = 4
    five = 5


class StyleFeature(BaseModel):
    label: str
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    examples: list[str]


class StyleProfile(BaseModel):
    id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    board_ids: list[str]
    anchor_pin_urls: list[str] = []
    style_context_path: Optional[str] = None
    features: Annotated[list[StyleFeature], Field(max_length=5)] = []


class UserPreferences(BaseModel):
    sizes: list[str] = []
    price_min: Optional[Annotated[float, Field(ge=0)]] = None
    price_max: Optional[Annotated[float, Field(ge=0)]] = None
    brand_allowlist: list[str] = []
    brand_blocklist: list[str] = []


class SearchStrategy(UserPreferences):
    keywords: list[str]


class Listing(BaseModel):
    id: str
    title: str
    price: Annotated[float, Field(ge=0)]
    brand: Optional[str] = None
    size: Optional[str] = None
    image_urls: list[str] = []
    vinted_url: str
    score: Optional[float] = None
    reasoning: Optional[str] = None
    feedback: Optional[FeedbackRating] = None


class ScoredListing(Listing):
    score: float
    reasoning: str


class PinterestBoard(BaseModel):
    id: str
    name: str
    thumbnail_url: Optional[str] = None


class PinterestPin(BaseModel):
    id: str
    image_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    link: Optional[str] = None
