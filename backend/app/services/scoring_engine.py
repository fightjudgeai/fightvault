"""Fight Judge AI — Core Scoring Engine.

All scoring formulas are implemented here with full transparency.
Named constants are defined at the top; no magic numbers buried inside functions.

Formula reference:
  RPS  — Round Performance Score (0–100 per round)
  FPS  — Fight Performance Score (0–100 per fight)
  FCS  — Fighter Career Score   (0–100 career)
  MMS  — Matchmaking Score      (0–100 per matchup)
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Weight constants — 3-round bouts
# ---------------------------------------------------------------------------
ROUND_WEIGHTS_3: list[float] = [0.30, 0.35, 0.35]

# Weight constants — 5-round bouts (championship / main events)
ROUND_WEIGHTS_5: list[float] = [0.15, 0.20, 0.25, 0.20, 0.20]

# FPS result bonuses
RESULT_BONUS_KO_TKO: float = 12.0
RESULT_BONUS_SUBMISSION: float = 10.0
RESULT_BONUS_DECISION: float = 5.0
RESULT_BONUS_NONE: float = 0.0

# FPS rolling average weights (most recent first, up to 5 fights)
FPS_LAST5_WEIGHTS: list[float] = [0.30, 0.25, 0.20, 0.15, 0.10]

# FCS component weights
FCS_WEIGHT_FPS_LAST5: float = 0.40
FCS_WEIGHT_WIN_RATE: float = 0.25
FCS_WEIGHT_FINISH_RATE: float = 0.20
FCS_WEIGHT_OPP_QUALITY: float = 0.15

# MMS component weights (ref: docs/SCORING.md)
MMS_WEIGHT_COMPETITIVENESS: float = 0.40
MMS_WEIGHT_ACTION_POTENTIAL: float = 0.30
MMS_WEIGHT_STYLE_CLASH: float = 0.20
MMS_WEIGHT_QUALITY_BALANCE: float = 0.10

# RPS sub-component weights (ref: docs/SCORING.md)
RPS_WEIGHT_STRIKING: float = 0.35
RPS_WEIGHT_GRAPPLING: float = 0.25
RPS_WEIGHT_CONTROL: float = 0.20
RPS_WEIGHT_FINISH_THREAT: float = 0.20

# Finish threat component weights
FINISH_THREAT_KO_WEIGHT: float = 0.60
FINISH_THREAT_SUB_WEIGHT: float = 0.40

# Confidence thresholds
CONFIDENCE_LOW_MAX_FIGHTS: int = 3     # < 3 fights → low
CONFIDENCE_MED_MAX_FIGHTS: int = 5     # < 5 fights → medium; else high
FCS_CONFIDENCE_LOW_FIGHTS: int = 3     # total_fights < 3 → low
FCS_CONFIDENCE_MED_FIGHTS: int = 10    # total_fights < 10 → medium; else high

# Maximum control time used as denominator for control_dom normalisation (seconds)
MAX_CONTROL_TIME_SECONDS: float = 300.0  # 5 minutes per round

# Score caps
FPS_MAX: float = 100.0
RPS_MAX: float = 100.0
FCS_MAX: float = 100.0
MMS_MAX: float = 100.0

# ---------------------------------------------------------------------------
# Style clash matrix — 4 primary styles
# Values represent entertainment/clash potential (0.0–1.0)
# Styles: striker, grappler, wrestler, bjj
# ---------------------------------------------------------------------------
STYLE_CLASH_MATRIX: dict[str, dict[str, float]] = {
    "striker": {
        "striker":  0.70,
        "grappler": 0.85,
        "wrestler": 0.80,
        "bjj":      0.88,
        "muay_thai": 0.65,
        "boxing":   0.60,
        "kickboxer": 0.68,
        "mixed":    0.75,
    },
    "grappler": {
        "striker":  0.85,
        "grappler": 0.55,
        "wrestler": 0.72,
        "bjj":      0.65,
        "muay_thai": 0.80,
        "boxing":   0.82,
        "kickboxer": 0.78,
        "mixed":    0.70,
    },
    "wrestler": {
        "striker":  0.80,
        "grappler": 0.72,
        "wrestler": 0.50,
        "bjj":      0.75,
        "muay_thai": 0.78,
        "boxing":   0.76,
        "kickboxer": 0.74,
        "mixed":    0.68,
    },
    "bjj": {
        "striker":  0.88,
        "grappler": 0.65,
        "wrestler": 0.75,
        "bjj":      0.45,
        "muay_thai": 0.85,
        "boxing":   0.86,
        "kickboxer": 0.84,
        "mixed":    0.72,
    },
    "muay_thai": {
        "striker":  0.65,
        "grappler": 0.80,
        "wrestler": 0.78,
        "bjj":      0.85,
        "muay_thai": 0.60,
        "boxing":   0.72,
        "kickboxer": 0.70,
        "mixed":    0.74,
    },
    "boxing": {
        "striker":  0.60,
        "grappler": 0.82,
        "wrestler": 0.76,
        "bjj":      0.86,
        "muay_thai": 0.72,
        "boxing":   0.58,
        "kickboxer": 0.68,
        "mixed":    0.71,
    },
    "kickboxer": {
        "striker":  0.68,
        "grappler": 0.78,
        "wrestler": 0.74,
        "bjj":      0.84,
        "muay_thai": 0.70,
        "boxing":   0.68,
        "kickboxer": 0.62,
        "mixed":    0.73,
    },
    "mixed": {
        "striker":  0.75,
        "grappler": 0.70,
        "wrestler": 0.68,
        "bjj":      0.72,
        "muay_thai": 0.74,
        "boxing":   0.71,
        "kickboxer": 0.73,
        "mixed":    0.65,
    },
}


# ---------------------------------------------------------------------------
# Data classes — inputs and outputs
# ---------------------------------------------------------------------------


@dataclass
class RoundStatsInput:
    """Raw per-fighter per-round statistics used as RPS input."""

    sig_strikes_landed: int
    sig_strikes_attempted: int
    takedowns_landed: int
    takedown_attempts: int
    sub_attempts: int
    control_time_seconds: int
    knockdowns: int


@dataclass
class RoundScoreResult:
    """Output of compute_rps() — sub-components and final RPS."""

    striking_eff: float    # 0.0–1.0
    grappling_eff: float   # 0.0–1.0
    control_dom: float     # 0.0–1.0
    finish_threat: float   # 0.0–1.0 (round-level)
    rps: float             # 0–100


@dataclass
class FightScoreResult:
    """Output of compute_fps() — base score, bonus, and final FPS."""

    fps_base: float
    result_bonus: float
    fps: float             # capped at FPS_MAX


@dataclass
class FPSRollingResult:
    """Output of compute_fps_last5()."""

    fps_last5_avg: float
    n_fights: int
    confidence: str        # "low" | "medium" | "high"


@dataclass
class FCSResult:
    """Output of compute_fcs()."""

    fcs: float             # 0–100
    confidence: str        # "low" | "medium" | "high"


@dataclass
class FinishThreatResult:
    """Output of compute_finish_threat()."""

    finish_threat: float   # 0.0–1.0
    ko_rate: float
    sub_rate: float
    confidence: str        # "low" | "medium" | "high"


@dataclass
class MMSResult:
    """Output of compute_mms() — Matchmaking Score with sub-components."""

    competitiveness: float     # 0–100
    action_potential: float    # 0–100
    style_clash: float         # 0–100 (from matrix × 100)
    quality_balance: float     # 0–100
    mms: float                 # 0–100 weighted composite


# ---------------------------------------------------------------------------
# 1. compute_rps
# ---------------------------------------------------------------------------


def compute_rps(stats: RoundStatsInput) -> RoundScoreResult:
    """Compute Round Performance Score for a single fighter in one round.

    Args:
        stats: Raw per-round statistics for one fighter.

    Returns:
        RoundScoreResult with all sub-components (0.0–1.0) and final RPS (0–100).
    """
    # Striking efficiency: sig_strikes_landed / sig_strikes_attempted
    # Falls back to 0 if no strikes attempted.
    striking_eff: float = (
        stats.sig_strikes_landed / stats.sig_strikes_attempted
        if stats.sig_strikes_attempted > 0
        else 0.0
    )
    striking_eff = min(striking_eff, 1.0)

    # Grappling efficiency: takedowns_landed / takedown_attempts
    # Sub-attempts contribute a flat bonus (capped at 1.0)
    if stats.takedown_attempts > 0:
        td_eff = stats.takedowns_landed / stats.takedown_attempts
    else:
        td_eff = 0.0
    sub_bonus = min(stats.sub_attempts * 0.10, 0.30)
    grappling_eff: float = min(td_eff + sub_bonus, 1.0)

    # Control dominance: proportion of round under control, normalised to 5 min
    control_dom: float = min(
        stats.control_time_seconds / MAX_CONTROL_TIME_SECONDS, 1.0
    )

    # Round-level finish threat: knockdowns (each = 0.25 bonus), capped at 1.0
    # Combined with sub attempts already captured in grappling; this is pure KD impact.
    kd_threat = min(stats.knockdowns * 0.25, 0.75)
    # Add sub attempt influence here too for finish context
    finish_threat: float = min(kd_threat + sub_bonus * 0.5, 1.0)

    # Weighted composite → RPS (0–100)
    rps_raw = (
        striking_eff * RPS_WEIGHT_STRIKING
        + grappling_eff * RPS_WEIGHT_GRAPPLING
        + control_dom * RPS_WEIGHT_CONTROL
        + finish_threat * RPS_WEIGHT_FINISH_THREAT
    )
    rps = min(rps_raw * RPS_MAX, RPS_MAX)

    return RoundScoreResult(
        striking_eff=striking_eff,
        grappling_eff=grappling_eff,
        control_dom=control_dom,
        finish_threat=finish_threat,
        rps=round(rps, 4),
    )


# ---------------------------------------------------------------------------
# 2. compute_fps
# ---------------------------------------------------------------------------


def compute_fps(
    round_scores: list[RoundScoreResult],
    scheduled_rounds: int,
    win_method: Optional[str] = None,
) -> FightScoreResult:
    """Compute Fight Performance Score for a fighter from their round scores.

    Args:
        round_scores: Ordered list of RoundScoreResult (earliest first).
        scheduled_rounds: 3 or 5 (determines weight vector).
        win_method: SQL enum value string or None for non-wins.

    Returns:
        FightScoreResult with fps_base, result_bonus, and fps (capped at 100).
    """
    if not round_scores:
        return FightScoreResult(fps_base=0.0, result_bonus=0.0, fps=0.0)

    # Select weight vector — pad or trim round_scores to match vector length
    if scheduled_rounds >= 5:
        weights = ROUND_WEIGHTS_5
    else:
        weights = ROUND_WEIGHTS_3

    # Align scores to weight vector
    n_weights = len(weights)
    scores_aligned = round_scores[:n_weights]
    weights_aligned = weights[: len(scores_aligned)]

    # Normalise weights so they sum to 1.0 (handles partial-round fights)
    weight_sum = sum(weights_aligned)
    if weight_sum == 0:
        return FightScoreResult(fps_base=0.0, result_bonus=0.0, fps=0.0)

    fps_base: float = sum(
        (w / weight_sum) * rs.rps
        for w, rs in zip(weights_aligned, scores_aligned)
    )

    # Result bonus
    result_bonus: float = _resolve_result_bonus(win_method)

    fps = min(fps_base + result_bonus, FPS_MAX)

    return FightScoreResult(
        fps_base=round(fps_base, 4),
        result_bonus=result_bonus,
        fps=round(fps, 4),
    )


def _resolve_result_bonus(win_method: Optional[str]) -> float:
    """Map a win_method string to its bonus value."""
    if win_method is None:
        return RESULT_BONUS_NONE
    wm = win_method.lower()
    if wm in ("ko", "tko"):
        return RESULT_BONUS_KO_TKO
    if wm == "submission":
        return RESULT_BONUS_SUBMISSION
    if wm in (
        "decision_unanimous",
        "decision_split",
        "decision_majority",
    ):
        return RESULT_BONUS_DECISION
    return RESULT_BONUS_NONE


# ---------------------------------------------------------------------------
# 3. compute_fps_last5
# ---------------------------------------------------------------------------


def compute_fps_last5(fight_scores: list[float]) -> FPSRollingResult:
    """Compute weighted rolling average of last 5 FPS values.

    Args:
        fight_scores: FPS values in descending chronological order (most recent first).

    Returns:
        FPSRollingResult with weighted average, fight count, and confidence.
    """
    scores = fight_scores[:5]  # cap at 5 most recent
    n = len(scores)

    if n == 0:
        return FPSRollingResult(fps_last5_avg=0.0, n_fights=0, confidence="low")

    weights = FPS_LAST5_WEIGHTS[:n]
    weight_sum = sum(weights)
    weighted_avg = sum(w * s for w, s in zip(weights, scores)) / weight_sum

    confidence: str
    if n < CONFIDENCE_LOW_MAX_FIGHTS:
        confidence = "low"
    elif n < CONFIDENCE_MED_MAX_FIGHTS:
        confidence = "medium"
    else:
        confidence = "high"

    return FPSRollingResult(
        fps_last5_avg=round(weighted_avg, 4),
        n_fights=n,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# 4. compute_fcs
# ---------------------------------------------------------------------------


def compute_fcs(
    fps_last5_avg: float,
    fps_last5_n: int,
    win_rate_adjusted: float,
    finish_rate: float,
    opponent_quality_avg: float,
    total_fights: int,
) -> FCSResult:
    """Compute Fighter Career Score.

    Formula:
        fcs = fps_last5_avg * 0.40
              + win_rate_adjusted * 100 * 0.25
              + finish_rate * 100 * 0.20
              + opponent_quality_avg * 0.15

    Args:
        fps_last5_avg: Weighted rolling FPS average (0–100).
        fps_last5_n: Number of fights included in fps_last5_avg.
        win_rate_adjusted: Win rate as a proportion (0.0–1.0).
        finish_rate: (ko_wins + sub_wins) / total_fights (0.0–1.0).
        opponent_quality_avg: Average FCS of opponents faced (0–100).
        total_fights: Total career bouts used for confidence calculation.

    Returns:
        FCSResult with fcs (0–100) and confidence level.
    """
    fcs_raw = (
        fps_last5_avg * FCS_WEIGHT_FPS_LAST5
        + win_rate_adjusted * 100.0 * FCS_WEIGHT_WIN_RATE
        + finish_rate * 100.0 * FCS_WEIGHT_FINISH_RATE
        + opponent_quality_avg * FCS_WEIGHT_OPP_QUALITY
    )
    fcs = min(max(fcs_raw, 0.0), FCS_MAX)

    confidence: str
    if total_fights < FCS_CONFIDENCE_LOW_FIGHTS:
        confidence = "low"
    elif total_fights < FCS_CONFIDENCE_MED_FIGHTS:
        confidence = "medium"
    else:
        confidence = "high"

    return FCSResult(fcs=round(fcs, 4), confidence=confidence)


# ---------------------------------------------------------------------------
# 5. compute_finish_threat
# ---------------------------------------------------------------------------


def compute_finish_threat(
    ko_wins: int,
    sub_wins: int,
    total_fights: int,
) -> FinishThreatResult:
    """Compute career-level finish threat ratio.

    Formula:
        finish_threat = min(ko_rate * 0.60 + sub_rate * 0.40, 1.0)

    Args:
        ko_wins: Career KO/TKO victories.
        sub_wins: Career submission victories.
        total_fights: Total career bouts.

    Returns:
        FinishThreatResult with finish_threat (0.0–1.0) and confidence.
    """
    if total_fights == 0:
        return FinishThreatResult(
            finish_threat=0.0, ko_rate=0.0, sub_rate=0.0, confidence="low"
        )

    ko_rate = ko_wins / total_fights
    sub_rate = sub_wins / total_fights
    finish_threat = min(
        ko_rate * FINISH_THREAT_KO_WEIGHT + sub_rate * FINISH_THREAT_SUB_WEIGHT,
        1.0,
    )

    confidence = "low" if total_fights < 5 else "medium" if total_fights < 10 else "high"

    return FinishThreatResult(
        finish_threat=round(finish_threat, 4),
        ko_rate=round(ko_rate, 4),
        sub_rate=round(sub_rate, 4),
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# 6. compute_volatility
# ---------------------------------------------------------------------------


def compute_volatility(fps_scores: list[float]) -> float:
    """Return population standard deviation of provided FPS scores.

    A higher value indicates inconsistent performance across fights.

    Args:
        fps_scores: List of FPS values for a fighter.

    Returns:
        Population std dev (0.0 if fewer than 2 data points).
    """
    if len(fps_scores) < 2:
        return 0.0
    mean = sum(fps_scores) / len(fps_scores)
    variance = sum((x - mean) ** 2 for x in fps_scores) / len(fps_scores)
    return round(math.sqrt(variance), 4)


# ---------------------------------------------------------------------------
# 8. compute_mms
# ---------------------------------------------------------------------------


def _get_style_clash(style_a: Optional[str], style_b: Optional[str]) -> float:
    """Look up style clash value from STYLE_CLASH_MATRIX.

    Falls back to 0.70 (moderate) when either style is unknown.
    """
    default = 0.70
    if style_a is None or style_b is None:
        return default
    row = STYLE_CLASH_MATRIX.get(style_a.lower())
    if row is None:
        return default
    return row.get(style_b.lower(), default)


def compute_mms(
    fcs_a: float,
    fcs_b: float,
    finish_threat_a: float,
    finish_threat_b: float,
    style_a: Optional[str],
    style_b: Optional[str],
    opp_quality_avg_a: float,
    opp_quality_avg_b: float,
) -> MMSResult:
    """Compute Matchmaking Score between two fighters.

    Formula (all sub-components normalised to 0–100):

        competitiveness  = 100 - |fcs_a - fcs_b|   (punishes large FCS gaps)
        action_potential = (finish_threat_a + finish_threat_b) / 2 * 100
        style_clash      = STYLE_CLASH_MATRIX[style_a][style_b] * 100
        quality_balance  = 100 - |opp_quality_avg_a - opp_quality_avg_b|

        mms = competitiveness  * 0.35
              + action_potential * 0.25
              + style_clash      * 0.20
              + quality_balance  * 0.20

    Args:
        fcs_a: Career score for fighter A (0–100).
        fcs_b: Career score for fighter B (0–100).
        finish_threat_a: Finish threat ratio for A (0.0–1.0).
        finish_threat_b: Finish threat ratio for B (0.0–1.0).
        style_a: Fighting style string for A (must be in STYLE_CLASH_MATRIX).
        style_b: Fighting style string for B.
        opp_quality_avg_a: Average opponent FCS faced by A (0–100).
        opp_quality_avg_b: Average opponent FCS faced by B (0–100).

    Returns:
        MMSResult with all sub-components and final MMS (0–100).
    """
    competitiveness = max(0.0, 100.0 - abs(fcs_a - fcs_b))
    action_potential = ((finish_threat_a + finish_threat_b) / 2.0) * 100.0
    style_clash = _get_style_clash(style_a, style_b) * 100.0
    quality_balance = max(0.0, 100.0 - abs(opp_quality_avg_a - opp_quality_avg_b))

    mms_raw = (
        competitiveness * MMS_WEIGHT_COMPETITIVENESS
        + action_potential * MMS_WEIGHT_ACTION_POTENTIAL
        + style_clash * MMS_WEIGHT_STYLE_CLASH
        + quality_balance * MMS_WEIGHT_QUALITY_BALANCE
    )
    mms = min(max(mms_raw, 0.0), MMS_MAX)

    return MMSResult(
        competitiveness=round(competitiveness, 4),
        action_potential=round(action_potential, 4),
        style_clash=round(style_clash, 4),
        quality_balance=round(quality_balance, 4),
        mms=round(mms, 4),
    )
