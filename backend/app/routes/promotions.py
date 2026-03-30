"""FastAPI router for the promotions domain."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import execute, fetch, fetchrow, get_db
from app.models.promotions import PromotionCreate, PromotionOut, PromotionUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/promotions", tags=["promotions"])


@router.get("", response_model=list[PromotionOut])
async def list_promotions(
    active_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: asyncpg.Connection = Depends(get_db),
) -> list[PromotionOut]:
    """List all promotions, ordered by name."""
    where = "WHERE active = true" if active_only else ""
    rows = await fetch(
        db,
        f"""
        SELECT p.*,
               COUNT(f.id) AS fighter_count
          FROM promotions p
          LEFT JOIN fighters f ON f.promotion_id = p.id AND f.is_active = true
        {where}
         GROUP BY p.id
         ORDER BY p.name ASC
         LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    return [PromotionOut(**dict(r)) for r in rows]


@router.post("", response_model=PromotionOut, status_code=status.HTTP_201_CREATED)
async def create_promotion(
    body: PromotionCreate,
    db: asyncpg.Connection = Depends(get_db),
) -> PromotionOut:
    """Create a new promotion."""
    existing = await fetchrow(
        db, "SELECT id FROM promotions WHERE slug = $1", body.slug
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already in use")

    row = await fetchrow(
        db,
        """
        INSERT INTO promotions (name, slug, logo_url, website, description,
                                city, state, country)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        RETURNING *
        """,
        body.name,
        body.slug,
        body.logo_url,
        body.website,
        body.description,
        body.city,
        body.state,
        body.country,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create promotion")
    return PromotionOut(**dict(row))


@router.get("/{promotion_id}", response_model=dict)
async def get_promotion(
    promotion_id: UUID,
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """Get promotion detail with fighter and fight counts."""
    row = await fetchrow(
        db,
        """
        SELECT p.*,
               COUNT(DISTINCT f.id)  AS fighter_count,
               COUNT(DISTINCT b.id)  AS bout_count
          FROM promotions p
          LEFT JOIN fighters f ON f.promotion_id = p.id
          LEFT JOIN events   e ON e.promotion_id = p.id
          LEFT JOIN bouts    b ON b.event_id     = e.id
         WHERE p.id = $1
         GROUP BY p.id
        """,
        promotion_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return dict(row)


@router.patch("/{promotion_id}", response_model=PromotionOut)
async def update_promotion(
    promotion_id: UUID,
    body: PromotionUpdate,
    db: asyncpg.Connection = Depends(get_db),
) -> PromotionOut:
    """Partially update promotion fields."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    set_clauses: list[str] = []
    args: list = []
    idx = 1
    for field, value in updates.items():
        set_clauses.append(f"{field} = ${idx}")
        args.append(value)
        idx += 1

    args.append(promotion_id)
    row = await fetchrow(
        db,
        f"""
        UPDATE promotions
           SET {", ".join(set_clauses)}, updated_at = NOW()
         WHERE id = ${idx}
         RETURNING *
        """,
        *args,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return PromotionOut(**dict(row))


@router.get("/{promotion_id}/fighters", response_model=list[dict])
async def promotion_fighters(
    promotion_id: UUID,
    weight_class: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    """List all fighters belonging to a promotion, with career scores."""
    # Verify promotion exists
    exists = await fetchrow(
        db, "SELECT id FROM promotions WHERE id = $1", promotion_id
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Promotion not found")

    conditions = ["f.promotion_id = $1"]
    args: list = [promotion_id]
    idx = 2

    if weight_class is not None:
        conditions.append(f"f.weight_class = ${idx}")
        args.append(weight_class)
        idx += 1

    if is_active is not None:
        conditions.append(f"f.is_active = ${idx}")
        args.append(is_active)
        idx += 1

    args.extend([limit, offset])
    rows = await fetch(
        db,
        f"""
        SELECT f.*,
               fcs.fcs,
               fcs.confidence AS fcs_confidence,
               fcs.computed_at AS fcs_computed_at
          FROM fighters f
          LEFT JOIN fighter_career_scores fcs ON fcs.fighter_id = f.id
         WHERE {" AND ".join(conditions)}
         ORDER BY f.last_name ASC, f.first_name ASC
         LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *args,
    )
    return [dict(r) for r in rows]
