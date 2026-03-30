"""FastAPI router for the fighters domain."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import execute, fetch, fetchrow, get_db
from app.models.fighters import (
    FighterCreate,
    FighterOut,
    FighterUpdate,
    WeightClass,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/fighters", tags=["fighters"])


async def _log_mutation(
    conn: asyncpg.Connection,
    action: str,
    entity_id: UUID,
    payload: dict,
) -> None:
    await execute(
        conn,
        """
        INSERT INTO operator_logs (action, entity_type, entity_id, payload)
        VALUES ($1, 'fighter', $2, $3::jsonb)
        """,
        action,
        entity_id,
        str(payload),
    )


@router.get("", response_model=list[dict])
async def search_fighters(
    name: Optional[str] = Query(None, description="Fuzzy name search (pg_trgm)"),
    weight_class: Optional[WeightClass] = Query(None),
    promotion_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    """Search fighters with optional fuzzy name matching and filters.

    Includes career score data (fcs, confidence) when available.
    """
    conditions: list[str] = []
    args: list = []
    idx = 1

    if name is not None:
        conditions.append(
            f"(f.first_name || ' ' || f.last_name) % ${idx} OR "
            f"f.nickname % ${idx}"
        )
        args.append(name)
        idx += 1

    if weight_class is not None:
        conditions.append(f"f.weight_class = ${idx}")
        args.append(weight_class.value)
        idx += 1

    if promotion_id is not None:
        conditions.append(f"f.promotion_id = ${idx}")
        args.append(promotion_id)
        idx += 1

    if is_active is not None:
        conditions.append(f"f.is_active = ${idx}")
        args.append(is_active)
        idx += 1

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Order by similarity when doing fuzzy name search
    order_clause = (
        f"ORDER BY similarity(f.first_name || ' ' || f.last_name, $1) DESC, "
        f"f.last_name ASC"
        if name is not None
        else "ORDER BY f.last_name ASC, f.first_name ASC"
    )

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
        {where_clause}
        {order_clause}
         LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *args,
    )
    return [dict(r) for r in rows]


@router.post("", response_model=FighterOut, status_code=status.HTTP_201_CREATED)
async def create_fighter(
    body: FighterCreate,
    db: asyncpg.Connection = Depends(get_db),
) -> FighterOut:
    """Create a new fighter record."""
    row = await fetchrow(
        db,
        """
        INSERT INTO fighters (first_name, last_name, nickname, weight_class,
                              fighting_style, date_of_birth, nationality, gym,
                              promotion_id, wins, losses, draws, no_contests,
                              ko_tko_wins, submission_wins, sherdog_id, tapology_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
        RETURNING *
        """,
        body.first_name,
        body.last_name,
        body.nickname,
        body.weight_class.value,
        body.fighting_style.value if body.fighting_style else None,
        body.date_of_birth,
        body.nationality,
        body.gym,
        body.promotion_id,
        body.wins,
        body.losses,
        body.draws,
        body.no_contests,
        body.ko_tko_wins,
        body.submission_wins,
        body.sherdog_id,
        body.tapology_id,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create fighter")

    await _log_mutation(db, "create", row["id"], body.model_dump())
    return FighterOut(**dict(row))


@router.get("/{fighter_id}", response_model=dict)
async def get_fighter(
    fighter_id: UUID,
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """Get fighter detail with career score and last 5 fight scores."""
    row = await fetchrow(
        db,
        """
        SELECT f.*,
               fcs.fcs,
               fcs.fps_last5_avg,
               fcs.fps_last5_n,
               fcs.win_rate_adjusted,
               fcs.finish_rate,
               fcs.opponent_quality_avg,
               fcs.volatility,
               fcs.confidence AS fcs_confidence,
               fcs.computed_at AS fcs_computed_at
          FROM fighters f
          LEFT JOIN fighter_career_scores fcs ON fcs.fighter_id = f.id
         WHERE f.id = $1
        """,
        fighter_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Fighter not found")

    result = dict(row)

    # Append last 5 fight scores
    score_rows = await fetch(
        db,
        """
        SELECT fs.*, b.event_id,
               opp.first_name || ' ' || opp.last_name AS opponent_name
          FROM fight_scores fs
          JOIN bouts b ON b.id = fs.bout_id
          JOIN fighters opp ON (
              CASE WHEN b.fighter_a_id = $1 THEN b.fighter_b_id
                   ELSE b.fighter_a_id END = opp.id
          )
         WHERE fs.fighter_id = $1
         ORDER BY fs.computed_at DESC
         LIMIT 5
        """,
        fighter_id,
    )
    result["last_5_fight_scores"] = [dict(r) for r in score_rows]
    return result


@router.patch("/{fighter_id}", response_model=FighterOut)
async def update_fighter(
    fighter_id: UUID,
    body: FighterUpdate,
    db: asyncpg.Connection = Depends(get_db),
) -> FighterOut:
    """Partially update fighter fields."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    set_clauses: list[str] = []
    args: list = []
    idx = 1
    for field, value in updates.items():
        set_clauses.append(f"{field} = ${idx}")
        args.append(value.value if hasattr(value, "value") else value)
        idx += 1

    args.append(fighter_id)
    row = await fetchrow(
        db,
        f"""
        UPDATE fighters
           SET {", ".join(set_clauses)}, updated_at = NOW()
         WHERE id = ${idx}
         RETURNING *
        """,
        *args,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Fighter not found")

    await _log_mutation(db, "update", fighter_id, updates)
    return FighterOut(**dict(row))


@router.get("/{fighter_id}/scores")
async def fighter_score_history(
    fighter_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    """Return full fight score history for a fighter."""
    rows = await fetch(
        db,
        """
        SELECT fs.*,
               b.event_id,
               b.weight_class,
               b.is_title_fight,
               opp.first_name || ' ' || opp.last_name AS opponent_name,
               opp.id AS opponent_id
          FROM fight_scores fs
          JOIN bouts b ON b.id = fs.bout_id
          JOIN fighters opp ON (
              CASE WHEN b.fighter_a_id = $1 THEN b.fighter_b_id
                   ELSE b.fighter_a_id END = opp.id
          )
         WHERE fs.fighter_id = $1
         ORDER BY fs.computed_at DESC
         LIMIT $2 OFFSET $3
        """,
        fighter_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]


@router.get("/{fighter_id}/fights")
async def fighter_fights(
    fighter_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    """Return all bouts for a fighter with results and opponent info."""
    rows = await fetch(
        db,
        """
        SELECT b.*,
               e.name AS event_name,
               e.event_date,
               opp.id AS opponent_id,
               opp.first_name || ' ' || opp.last_name AS opponent_name,
               opp.nickname AS opponent_nickname,
               CASE WHEN b.fighter_a_id = $1
                    THEN b.result_fighter_a
                    ELSE b.result_fighter_b
               END AS fighter_result
          FROM bouts b
          JOIN events e ON e.id = b.event_id
          JOIN fighters opp ON (
              CASE WHEN b.fighter_a_id = $1 THEN b.fighter_b_id
                   ELSE b.fighter_a_id END = opp.id
          )
         WHERE b.fighter_a_id = $1 OR b.fighter_b_id = $1
         ORDER BY e.event_date DESC NULLS LAST, b.created_at DESC
         LIMIT $2 OFFSET $3
        """,
        fighter_id,
        limit,
        offset,
    )
    return [dict(r) for r in rows]
