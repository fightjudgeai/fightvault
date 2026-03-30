"""Shared Pydantic base models used across the application."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UUIDModel(BaseModel):
    """Base model that includes a UUID primary key."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID


class TimestampModel(BaseModel):
    """Base model that includes created_at and updated_at audit timestamps."""

    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Query-string pagination parameters."""

    limit: int = 50
    offset: int = 0


class SuccessResponse(BaseModel):
    """Generic success/failure envelope returned by mutation endpoints."""

    success: bool
    message: str
