"""Pydantic models for scoring outputs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConfidenceLevel(str, Enum):
    """Statistical confidence level for a computed score."""

    low = "low"
    medium = "medium"
    high = "high"


class RoundScoreOut(BaseModel):
    """Computed Round Performance Score (RPS) for a single fighter in one round."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    bout_id: Optional[UUID] = None
    fighter_id: Optional[UUID] = None
    round_number: Optional[int] = None

    # RPS sub-components (each 0.0–1.0)
    striking_eff: float
    grappling_eff: float
    control_dom: float
    finish_threat: float

    # Final RPS (0–100)
    rps: float


class FightScoreOut(BaseModel):
    """Computed Fight Performance Score (FPS) for one fighter in one bout."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    bout_id: Optional[UUID] = None
    fighter_id: Optional[UUID] = None

    fps_base: float
    result_bonus: float
    fps: float

    # Derived metrics embedded for convenience
    finish_threat: Optional[float] = None
    opponent_fcs: Optional[float] = None

    computed_at: Optional[datetime] = None


class FighterCareerScoreOut(BaseModel):
    """Fighter Career Score (FCS) with full breakdown."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    fighter_id: Optional[UUID] = None

    # FCS inputs
    fps_last5_avg: float
    fps_last5_n: int
    win_rate_adjusted: float
    finish_rate: float
    opponent_quality_avg: float

    # FCS output
    fcs: float

    # Volatility metric
    volatility: Optional[float] = None

    confidence: ConfidenceLevel
    computed_at: Optional[datetime] = None
