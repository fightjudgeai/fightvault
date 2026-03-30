"""Pydantic models for the fights/bouts domain."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.fighters import WeightClass


class FightResult(str, Enum):
    """Per-fighter result of a bout matching the SQL enum."""

    win = "win"
    loss = "loss"
    draw = "draw"
    no_contest = "no_contest"
    no_decision = "no_decision"


class WinMethod(str, Enum):
    """Method by which the bout ended matching the SQL enum."""

    ko = "ko"
    tko = "tko"
    submission = "submission"
    decision_unanimous = "decision_unanimous"
    decision_split = "decision_split"
    decision_majority = "decision_majority"
    dq = "dq"
    no_contest = "no_contest"
    draw = "draw"


class BoutCreate(BaseModel):
    """Payload for creating a new bout on an event card."""

    event_id: UUID
    fighter_a_id: UUID
    fighter_b_id: UUID
    weight_class: WeightClass
    scheduled_rounds: int = 3
    is_title_fight: bool = False
    is_main_event: bool = False
    bout_order: Optional[int] = None
    notes: Optional[str] = None


class BoutUpdate(BaseModel):
    """Payload for partially updating bout metadata (pre-fight fields only)."""

    weight_class: Optional[WeightClass] = None
    scheduled_rounds: Optional[int] = None
    is_title_fight: Optional[bool] = None
    is_main_event: Optional[bool] = None
    bout_order: Optional[int] = None
    notes: Optional[str] = None


class FightResultUpdate(BaseModel):
    """Payload for recording the official result of a completed bout."""

    result_fighter_a: FightResult
    result_fighter_b: FightResult
    win_method: Optional[WinMethod] = None
    end_round: Optional[int] = None
    end_time_seconds: Optional[int] = None
    actual_rounds: Optional[int] = None


class BoutOut(BaseModel):
    """Full bout record returned by GET endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    fighter_a_id: UUID
    fighter_b_id: UUID
    weight_class: WeightClass
    scheduled_rounds: int
    actual_rounds: Optional[int] = None
    is_title_fight: bool
    is_main_event: bool
    bout_order: Optional[int] = None
    result_fighter_a: Optional[FightResult] = None
    result_fighter_b: Optional[FightResult] = None
    win_method: Optional[WinMethod] = None
    end_round: Optional[int] = None
    end_time_seconds: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RoundStatsCreate(BaseModel):
    """Per-fighter per-round statistics submitted after a bout."""

    bout_id: UUID
    fighter_id: UUID
    round_number: int
    sig_strikes_landed: int = 0
    sig_strikes_attempted: int = 0
    total_strikes_landed: int = 0
    total_strikes_attempted: int = 0
    takedowns_landed: int = 0
    takedown_attempts: int = 0
    sub_attempts: int = 0
    control_time_seconds: int = 0
    knockdowns: int = 0
    distance_strikes_landed: int = 0
    clinch_strikes_landed: int = 0
    ground_strikes_landed: int = 0


class RoundStatsOut(BaseModel):
    """Round statistics record returned by GET endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bout_id: UUID
    fighter_id: UUID
    round_number: int
    sig_strikes_landed: int
    sig_strikes_attempted: int
    total_strikes_landed: int
    total_strikes_attempted: int
    takedowns_landed: int
    takedown_attempts: int
    sub_attempts: int
    control_time_seconds: int
    knockdowns: int
    distance_strikes_landed: int
    clinch_strikes_landed: int
    ground_strikes_landed: int
    created_at: datetime
