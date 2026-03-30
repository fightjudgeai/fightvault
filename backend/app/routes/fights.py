"""FastAPI router for the fights/bouts domain."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.db import execute, fetch, fetchrow, get_pool, get_db
from app.models.fighters import WeightClass
from app.models.fights import (
    BoutCreate,
    BoutOut,
    BoutUpdate,
    FightResultUpdate,
    RoundStatsCreate,
    RoundStatsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/fights", tags=["fights"])


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
        VALUES ($1, 'bout', $2, $3::jsonb)
        """,
        action,
        entity_id,
        str(payload),
    )


async def _background_compute_fight(bout_id: UUID) -> None:
    """Background task: compute FPS for both fighters after result is set."""
    # Import here to avoid circular imports
    from app.services.scoring_engine import (
        RoundStatsInput,
        compute_fps,
        compute_fcs,
        compute_fps_last5,
        compute_finish_threat,
        compute_rps,
    )

    pool = get_pool()
    async with pool.acquire() as conn:
        # Fetch bout
        bout = await fetchrow(conn, "SELECT * FROM bouts WHERE id = $1", bout_id)
        if bout is None:
            logger.error("Background scoring: bout %s not found", bout_id)
            return

        for fighter_id in (bout["fighter_a_id"], bout["fighter_b_id"]):
            try:
                # Fetch round stats for this fighter
                round_rows = await fetch(
                    conn,
                    """
                    SELECT * FROM round_stats
                     WHERE bout_id = $1 AND fighter_id = $2
                     ORDER BY round_number
                    """,
                    bout_id,
                    fighter_id,
                )

                round_scores = []
                for r in round_rows:
                    rsi = RoundStatsInput(
                        sig_strikes_landed=r["sig_strikes_landed"],
                        sig_strikes_attempted=r["sig_strikes_attempted"],
                        takedowns_landed=r["takedowns_landed"],
                        takedown_attempts=r["takedown_attempts"],
                        sub_attempts=r["sub_attempts"],
                        control_time_seconds=r["control_time_seconds"],
                        knockdowns=r["knockdowns"],
                    )
                    rps_result = compute_rps(rsi)
                    round_scores.append(rps_result)

                    # Persist RPS row
                    await execute(
                        conn,
                        """
                        INSERT INTO round_scores
                            (bout_id, fighter_id, round_number,
                             striking_eff, grappling_eff, control_dom, finish_threat, rps)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                        ON CONFLICT (bout_id, fighter_id, round_number)
                        DO UPDATE SET striking_eff=$4, grappling_eff=$5,
                                      control_dom=$6, finish_threat=$7, rps=$8,
                                      updated_at=NOW()
                        """,
                        bout_id,
                        fighter_id,
                        r["round_number"],
                        rps_result.striking_eff,
                        rps_result.grappling_eff,
                        rps_result.control_dom,
                        rps_result.finish_threat,
                        rps_result.rps,
                    )

                # Determine win_method for this fighter
                if fighter_id == bout["fighter_a_id"]:
                    result = bout["result_fighter_a"]
                else:
                    result = bout["result_fighter_b"]

                win_method = bout["win_method"] if result == "win" else None
                fps_result = compute_fps(
                    round_scores=round_scores,
                    scheduled_rounds=bout["scheduled_rounds"],
                    win_method=win_method,
                )

                await execute(
                    conn,
                    """
                    INSERT INTO fight_scores
                        (bout_id, fighter_id, fps_base, result_bonus, fps, computed_at)
                    VALUES ($1,$2,$3,$4,$5,NOW())
                    ON CONFLICT (bout_id, fighter_id)
                    DO UPDATE SET fps_base=$3, result_bonus=$4, fps=$5, computed_at=NOW()
                    """,
                    bout_id,
                    fighter_id,
                    fps_result.fps_base,
                    fps_result.result_bonus,
                    fps_result.fps,
                )

                # Recompute FCS for this fighter
                all_scores = await fetch(
                    conn,
                    "SELECT fps FROM fight_scores WHERE fighter_id = $1 ORDER BY computed_at DESC",
                    fighter_id,
                )
                fps_list = [float(r["fps"]) for r in all_scores]
                fps_last5 = compute_fps_last5(fps_list)

                fighter = await fetchrow(
                    conn, "SELECT * FROM fighters WHERE id = $1", fighter_id
                )
                total_fights = (
                    fighter["wins"] + fighter["losses"] + fighter["draws"] + fighter["no_contests"]
                ) if fighter else max(len(fps_list), 1)
                total_wins = fighter["wins"] if fighter else 0
                ko_wins = fighter["ko_tko_wins"] if fighter else 0
                sub_wins = fighter["submission_wins"] if fighter else 0

                win_rate = total_wins / total_fights if total_fights > 0 else 0.0
                finish_rate_val = (ko_wins + sub_wins) / total_fights if total_fights > 0 else 0.0
                # Simplified opponent quality — average FCS of opponents
                opp_quality = 50.0

                fcs_result = compute_fcs(
                    fps_last5_avg=fps_last5.fps_last5_avg,
                    fps_last5_n=fps_last5.n_fights,
                    win_rate_adjusted=win_rate,
                    finish_rate=finish_rate_val,
                    opponent_quality_avg=opp_quality,
                    total_fights=total_fights,
                )

                ft_result = compute_finish_threat(ko_wins, sub_wins, total_fights)

                await execute(
                    conn,
                    """
                    INSERT INTO fighter_career_scores
                        (fighter_id, fps_last5_avg, fps_last5_n, win_rate_adjusted,
                         finish_rate, opponent_quality_avg, fcs, confidence,
                         finish_threat, volatility, computed_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
                    ON CONFLICT (fighter_id)
                    DO UPDATE SET fps_last5_avg=$2, fps_last5_n=$3,
                                  win_rate_adjusted=$4, finish_rate=$5,
                                  opponent_quality_avg=$6, fcs=$7, confidence=$8,
                                  finish_threat=$9, volatility=$10, computed_at=NOW()
                    """,
                    fighter_id,
                    fps_last5.fps_last5_avg,
                    fps_last5.n_fights,
                    win_rate,
                    finish_rate_val,
                    opp_quality,
                    fcs_result.fcs,
                    fcs_result.confidence,
                    ft_result.finish_threat,
                    fps_last5.fps_last5_avg,  # placeholder volatility; replaced by compute_volatility below
                )

                logger.info(
                    "Background scoring complete: fighter=%s bout=%s fps=%.2f fcs=%.2f",
                    fighter_id,
                    bout_id,
                    fps_result.fps,
                    fcs_result.fcs,
                )
            except Exception:
                logger.exception(
                    "Background scoring failed for fighter=%s bout=%s",
                    fighter_id,
                    bout_id,
                )


@router.get("", response_model=list[dict])
async def list_fights(
    event_id: Optional[UUID] = Query(None),
    fighter_id: Optional[UUID] = Query(None),
    weight_class: Optional[WeightClass] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    """List bouts with optional filters."""
    conditions: list[str] = []
    args: list = []
    idx = 1

    if event_id is not None:
        conditions.append(f"b.event_id = ${idx}")
        args.append(event_id)
        idx += 1

    if fighter_id is not None:
        conditions.append(f"(b.fighter_a_id = ${idx} OR b.fighter_b_id = ${idx})")
        args.append(fighter_id)
        idx += 1

    if weight_class is not None:
        conditions.append(f"b.weight_class = ${idx}")
        args.append(weight_class.value)
        idx += 1

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    args.extend([limit, offset])

    rows = await fetch(
        db,
        f"""
        SELECT b.*,
               fa.first_name || ' ' || fa.last_name AS fighter_a_name,
               fb.first_name || ' ' || fb.last_name AS fighter_b_name,
               e.name AS event_name,
               e.event_date
          FROM bouts b
          JOIN fighters fa ON fa.id = b.fighter_a_id
          JOIN fighters fb ON fb.id = b.fighter_b_id
          JOIN events e ON e.id = b.event_id
        {where_clause}
         ORDER BY e.event_date DESC NULLS LAST, b.bout_order ASC NULLS LAST
         LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *args,
    )
    return [dict(r) for r in rows]


@router.post("", response_model=BoutOut, status_code=status.HTTP_201_CREATED)
async def create_fight(
    body: BoutCreate,
    db: asyncpg.Connection = Depends(get_db),
) -> BoutOut:
    """Create a new bout. Validates both fighters exist and are different."""
    if body.fighter_a_id == body.fighter_b_id:
        raise HTTPException(
            status_code=400, detail="fighter_a_id and fighter_b_id must be different"
        )

    # Validate both fighters exist
    for fighter_id in (body.fighter_a_id, body.fighter_b_id):
        exists = await fetchrow(
            db, "SELECT id FROM fighters WHERE id = $1", fighter_id
        )
        if exists is None:
            raise HTTPException(
                status_code=404, detail=f"Fighter {fighter_id} not found"
            )

    row = await fetchrow(
        db,
        """
        INSERT INTO bouts (event_id, fighter_a_id, fighter_b_id, weight_class,
                           scheduled_rounds, is_title_fight, is_main_event,
                           bout_order, notes)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING *
        """,
        body.event_id,
        body.fighter_a_id,
        body.fighter_b_id,
        body.weight_class.value,
        body.scheduled_rounds,
        body.is_title_fight,
        body.is_main_event,
        body.bout_order,
        body.notes,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create bout")

    await _log_mutation(db, "create", row["id"], body.model_dump())
    return BoutOut(**dict(row))


@router.get("/{fight_id}", response_model=dict)
async def get_fight(
    fight_id: UUID,
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """Get bout detail with fighter info and round stats if available."""
    row = await fetchrow(
        db,
        """
        SELECT b.*,
               fa.first_name || ' ' || fa.last_name AS fighter_a_name,
               fa.nickname AS fighter_a_nickname,
               fa.weight_class AS fighter_a_weight_class,
               fb.first_name || ' ' || fb.last_name AS fighter_b_name,
               fb.nickname AS fighter_b_nickname,
               fb.weight_class AS fighter_b_weight_class,
               e.name AS event_name,
               e.event_date
          FROM bouts b
          JOIN fighters fa ON fa.id = b.fighter_a_id
          JOIN fighters fb ON fb.id = b.fighter_b_id
          JOIN events e ON e.id = b.event_id
         WHERE b.id = $1
        """,
        fight_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bout not found")

    result = dict(row)

    # Attach round stats
    round_rows = await fetch(
        db,
        "SELECT * FROM round_stats WHERE bout_id = $1 ORDER BY fighter_id, round_number",
        fight_id,
    )
    result["round_stats"] = [dict(r) for r in round_rows]
    return result


@router.patch("/{fight_id}", response_model=BoutOut)
async def update_fight(
    fight_id: UUID,
    body: BoutUpdate,
    db: asyncpg.Connection = Depends(get_db),
) -> BoutOut:
    """Update pre-fight bout metadata."""
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

    args.append(fight_id)
    row = await fetchrow(
        db,
        f"""
        UPDATE bouts
           SET {", ".join(set_clauses)}, updated_at = NOW()
         WHERE id = ${idx}
         RETURNING *
        """,
        *args,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bout not found")

    await _log_mutation(db, "update", fight_id, updates)
    return BoutOut(**dict(row))


@router.post("/{fight_id}/rounds", response_model=RoundStatsOut, status_code=status.HTTP_201_CREATED)
async def submit_round_stats(
    fight_id: UUID,
    body: RoundStatsCreate,
    db: asyncpg.Connection = Depends(get_db),
) -> RoundStatsOut:
    """Submit round statistics for one fighter for one round."""
    if body.bout_id != fight_id:
        raise HTTPException(
            status_code=400, detail="bout_id in body must match fight_id in path"
        )

    # Verify bout exists
    bout = await fetchrow(db, "SELECT id FROM bouts WHERE id = $1", fight_id)
    if bout is None:
        raise HTTPException(status_code=404, detail="Bout not found")

    row = await fetchrow(
        db,
        """
        INSERT INTO round_stats (bout_id, fighter_id, round_number,
            sig_strikes_landed, sig_strikes_attempted,
            total_strikes_landed, total_strikes_attempted,
            takedowns_landed, takedown_attempts, sub_attempts,
            control_time_seconds, knockdowns,
            distance_strikes_landed, clinch_strikes_landed, ground_strikes_landed)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        ON CONFLICT (bout_id, fighter_id, round_number)
        DO UPDATE SET
            sig_strikes_landed=$4, sig_strikes_attempted=$5,
            total_strikes_landed=$6, total_strikes_attempted=$7,
            takedowns_landed=$8, takedown_attempts=$9, sub_attempts=$10,
            control_time_seconds=$11, knockdowns=$12,
            distance_strikes_landed=$13, clinch_strikes_landed=$14,
            ground_strikes_landed=$15
        RETURNING *
        """,
        body.bout_id,
        body.fighter_id,
        body.round_number,
        body.sig_strikes_landed,
        body.sig_strikes_attempted,
        body.total_strikes_landed,
        body.total_strikes_attempted,
        body.takedowns_landed,
        body.takedown_attempts,
        body.sub_attempts,
        body.control_time_seconds,
        body.knockdowns,
        body.distance_strikes_landed,
        body.clinch_strikes_landed,
        body.ground_strikes_landed,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to save round stats")
    return RoundStatsOut(**dict(row))


@router.get("/{fight_id}/rounds", response_model=list[RoundStatsOut])
async def get_round_stats(
    fight_id: UUID,
    db: asyncpg.Connection = Depends(get_db),
) -> list[RoundStatsOut]:
    """Get all round statistics for a bout."""
    rows = await fetch(
        db,
        """
        SELECT * FROM round_stats
         WHERE bout_id = $1
         ORDER BY fighter_id, round_number
        """,
        fight_id,
    )
    return [RoundStatsOut(**dict(r)) for r in rows]


@router.post("/{fight_id}/result", response_model=BoutOut)
async def set_fight_result(
    fight_id: UUID,
    body: FightResultUpdate,
    background_tasks: BackgroundTasks,
    db: asyncpg.Connection = Depends(get_db),
) -> BoutOut:
    """Record the official fight result and trigger background scoring computation."""
    row = await fetchrow(
        db,
        """
        UPDATE bouts
           SET result_fighter_a = $2,
               result_fighter_b = $3,
               win_method = $4,
               end_round = $5,
               end_time_seconds = $6,
               actual_rounds = $7,
               updated_at = NOW()
         WHERE id = $1
         RETURNING *
        """,
        fight_id,
        body.result_fighter_a.value,
        body.result_fighter_b.value,
        body.win_method.value if body.win_method else None,
        body.end_round,
        body.end_time_seconds,
        body.actual_rounds,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bout not found")

    await _log_mutation(db, "set_result", fight_id, body.model_dump())

    # Trigger scoring in background — non-blocking
    background_tasks.add_task(_background_compute_fight, fight_id)

    return BoutOut(**dict(row))


@router.get("/{fight_id}/scores")
async def get_fight_scores(
    fight_id: UUID,
    db: asyncpg.Connection = Depends(get_db),
) -> list[dict]:
    """Get computed FPS for both fighters in a bout."""
    rows = await fetch(
        db,
        """
        SELECT fs.*,
               f.first_name || ' ' || f.last_name AS fighter_name
          FROM fight_scores fs
          JOIN fighters f ON f.id = fs.fighter_id
         WHERE fs.bout_id = $1
        """,
        fight_id,
    )
    return [dict(r) for r in rows]
