"""Pydantic models for the promotions domain."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class PromotionCreate(BaseModel):
    name: str
    slug: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "US"

    @field_validator("slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    active: Optional[bool] = None


class PromotionOut(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    active: bool
    created_at: datetime
    updated_at: datetime
