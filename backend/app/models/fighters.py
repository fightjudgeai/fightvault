"""Pydantic models for the fighters domain."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WeightClass(str, Enum):
    """MMA weight classes matching the SQL enum."""

    strawweight = "strawweight"
    flyweight = "flyweight"
    bantamweight = "bantamweight"
    featherweight = "featherweight"
    lightweight = "lightweight"
    welterweight = "welterweight"
    middleweight = "middleweight"
    light_heavyweight = "light_heavyweight"
    heavyweight = "heavyweight"
    super_heavyweight = "super_heavyweight"


class FightingStyle(str, Enum):
    """Primary fighting style matching the SQL enum."""

    striker = "striker"
    grappler = "grappler"
    wrestler = "wrestler"
    bjj = "bjj"
    muay_thai = "muay_thai"
    boxing = "boxing"
    kickboxer = "kickboxer"
    mixed = "mixed"


class FighterCreate(BaseModel):
    """Payload for creating a new fighter record."""

    first_name: str
    last_name: str
    nickname: Optional[str] = None
    weight_class: WeightClass
    fighting_style: Optional[FightingStyle] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    gym: Optional[str] = None
    promotion_id: Optional[UUID] = None
    wins: int = 0
    losses: int = 0
    draws: int = 0
    no_contests: int = 0
    ko_tko_wins: int = 0
    submission_wins: int = 0
    sherdog_id: Optional[str] = None
    tapology_id: Optional[str] = None


class FighterUpdate(BaseModel):
    """Payload for partially updating an existing fighter record.

    All fields are optional; only provided fields will be updated.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None
    weight_class: Optional[WeightClass] = None
    fighting_style: Optional[FightingStyle] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    gym: Optional[str] = None
    promotion_id: Optional[UUID] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    draws: Optional[int] = None
    no_contests: Optional[int] = None
    ko_tko_wins: Optional[int] = None
    submission_wins: Optional[int] = None
    is_active: Optional[bool] = None
    sherdog_id: Optional[str] = None
    tapology_id: Optional[str] = None


class FighterOut(BaseModel):
    """Full fighter record returned by GET endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    nickname: Optional[str] = None
    weight_class: WeightClass
    fighting_style: Optional[FightingStyle] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    gym: Optional[str] = None
    promotion_id: Optional[UUID] = None
    wins: int
    losses: int
    draws: int
    no_contests: int
    ko_tko_wins: int
    submission_wins: int
    is_active: bool
    sherdog_id: Optional[str] = None
    tapology_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
