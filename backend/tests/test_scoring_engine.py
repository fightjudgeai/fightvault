"""
Tests for Fight Judge AI scoring engine.

All formulas tested against hand-calculated expected values.
No mocks — pure function tests only (scoring_engine has no DB deps).
"""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.scoring_engine import (
    compute_rps,
    compute_fps,
    compute_fps_last5,
    compute_fcs,
    compute_finish_threat,
    compute_volatility,
    compute_mms,
    RoundStatsInput,
    STYLE_CLASH_MATRIX,
)


# ============================================================
# RPS Tests
# ============================================================

class TestComputeRPS:
    def test_dominant_striker_round(self):
        """Fighter lands 15/20 sig strikes, no grappling, 2 KDs."""
        stats = RoundStatsInput(
            sig_strikes_landed=15,
            sig_strikes_attempted=20,
            takedowns_landed=0,
            takedown_attempts=0,
            sub_attempts=0,
            control_time_seconds=0,
            knockdowns=2,
        )
        result = compute_rps(stats)
        # striking_eff = 15/20 = 0.75
        # grappling_eff = 0 (no attempts)
        # control_dom = 0
        # finish_threat = min(2*0.35, 1.0) = 0.70
        expected_raw = 0.75 * 0.35 + 0.0 * 0.25 + 0.0 * 0.20 + 0.70 * 0.20
        assert abs(result.rps - expected_raw * 100) < 0.1
        assert result.striking_eff == pytest.approx(0.75, abs=0.001)
        assert result.finish_threat == pytest.approx(0.70, abs=0.001)

    def test_dominant_wrestler_round(self):
        """Fighter takes down 3/4, controls 4 minutes."""
        stats = RoundStatsInput(
            sig_strikes_landed=5,
            sig_strikes_attempted=10,
            takedowns_landed=3,
            takedown_attempts=4,
            sub_attempts=1,
            control_time_seconds=240,
            knockdowns=0,
        )
        result = compute_rps(stats)
        striking_eff = 5 / 10
        grappling_eff = (3 * 3 + 1 * 2) / (4 + 1)  # 11/5 = 2.2, but capped behavior
        # grappling_eff is capped before weighting in formula
        control_dom = min(240 / 300, 1.0)  # 0.80
        assert result.control_dom == pytest.approx(control_dom, abs=0.001)
        assert result.rps >= 0
        assert result.rps <= 100

    def test_zero_stats_round(self):
        """Fighter lands nothing — minimal RPS."""
        stats = RoundStatsInput(
            sig_strikes_landed=0,
            sig_strikes_attempted=0,
            takedowns_landed=0,
            takedown_attempts=0,
            sub_attempts=0,
            control_time_seconds=0,
            knockdowns=0,
        )
        result = compute_rps(stats)
        assert result.rps == pytest.approx(0.0, abs=0.01)

    def test_perfect_control_round(self):
        """Fighter controls entire round."""
        stats = RoundStatsInput(
            sig_strikes_landed=0,
            sig_strikes_attempted=0,
            takedowns_landed=1,
            takedown_attempts=1,
            sub_attempts=0,
            control_time_seconds=300,
            knockdowns=0,
        )
        result = compute_rps(stats)
        assert result.control_dom == pytest.approx(1.0, abs=0.001)
        assert result.rps > 0

    def test_rps_never_exceeds_100(self):
        """Max possible stats should not produce RPS > 100."""
        stats = RoundStatsInput(
            sig_strikes_landed=100,
            sig_strikes_attempted=100,
            takedowns_landed=10,
            takedown_attempts=10,
            sub_attempts=5,
            control_time_seconds=300,
            knockdowns=5,
        )
        result = compute_rps(stats)
        assert result.rps <= 100.0

    def test_finish_threat_capped_at_1(self):
        """Many knockdowns should not push finish_threat above 1.0."""
        stats = RoundStatsInput(
            sig_strikes_landed=0,
            sig_strikes_attempted=0,
            takedowns_landed=0,
            takedown_attempts=0,
            sub_attempts=0,
            control_time_seconds=0,
            knockdowns=10,
        )
        result = compute_rps(stats)
        assert result.finish_threat <= 1.0


# ============================================================
# FPS Tests
# ============================================================

class TestComputeFPS:
    def _make_round_scores(self, rps_values):
        """Helper: create minimal RoundScoreResult list from RPS values."""
        from app.services.scoring_engine import RoundScoreResult
        return [
            RoundScoreResult(
                striking_eff=0.5, grappling_eff=0.5,
                control_dom=0.5, finish_threat=0.5,
                rps=rps
            )
            for rps in rps_values
        ]

    def test_three_round_win_by_ko(self):
        """3-round fight, winner by KO in R3."""
        rounds = self._make_round_scores([60.0, 70.0, 80.0])
        result = compute_fps(rounds, scheduled_rounds=3, win_method="ko_tko")
        # fps_base = 60*0.30 + 70*0.35 + 80*0.35 = 18 + 24.5 + 28 = 70.5
        # result_bonus = 12
        # fps = min(82.5, 100)
        assert result.fps_base == pytest.approx(70.5, abs=0.1)
        assert result.result_bonus == 12
        assert result.fps == pytest.approx(82.5, abs=0.1)

    def test_three_round_loss(self):
        """Loser gets no result bonus."""
        rounds = self._make_round_scores([60.0, 70.0, 80.0])
        result = compute_fps(rounds, scheduled_rounds=3, win_method=None)
        assert result.result_bonus == 0
        assert result.fps == pytest.approx(70.5, abs=0.1)

    def test_fps_capped_at_100(self):
        """Very high RPS + KO bonus should not exceed 100."""
        rounds = self._make_round_scores([95.0, 95.0, 95.0])
        result = compute_fps(rounds, scheduled_rounds=3, win_method="ko_tko")
        assert result.fps <= 100.0

    def test_five_round_weights(self):
        """5-round fight uses correct weights."""
        rounds = self._make_round_scores([50.0, 60.0, 70.0, 80.0, 90.0])
        result = compute_fps(rounds, scheduled_rounds=5, win_method="decision_unanimous")
        # 50*0.15 + 60*0.20 + 70*0.25 + 80*0.20 + 90*0.20 = 7.5+12+17.5+16+18 = 71.0
        # +5 decision bonus = 76.0
        assert result.fps_base == pytest.approx(71.0, abs=0.1)
        assert result.fps == pytest.approx(76.0, abs=0.1)

    def test_early_finish_renormalizes_weights(self):
        """Fight ending in R1 of a 3-round fight only uses R1 RPS."""
        rounds = self._make_round_scores([80.0])  # only 1 round completed
        result = compute_fps(rounds, scheduled_rounds=3, win_method="ko_tko")
        # Only 1 round — weight renormalizes to 1.0
        # fps_base = 80 * 1.0 = 80
        # + 12 = 92
        assert result.fps == pytest.approx(92.0, abs=0.1)


# ============================================================
# FPS_Last5 Tests
# ============================================================

class TestComputeFPSLast5:
    def test_five_fights_high_confidence(self):
        """5 fights gives high confidence."""
        result = compute_fps_last5([80.0, 75.0, 70.0, 65.0, 60.0])
        # weights: [0.30, 0.25, 0.20, 0.15, 0.10] (most recent first)
        expected = 80*0.30 + 75*0.25 + 70*0.20 + 65*0.15 + 60*0.10
        assert result.fps_last5_avg == pytest.approx(expected, abs=0.1)
        assert result.confidence == "high"
        assert result.n_fights == 5

    def test_three_fights_medium_confidence(self):
        result = compute_fps_last5([70.0, 65.0, 60.0])
        assert result.confidence == "medium"
        assert result.n_fights == 3

    def test_two_fights_low_confidence(self):
        result = compute_fps_last5([70.0, 60.0])
        assert result.confidence == "low"
        assert result.n_fights == 2

    def test_empty_fights(self):
        result = compute_fps_last5([])
        assert result.fps_last5_avg is None
        assert result.confidence == "low"
        assert result.n_fights == 0

    def test_weights_renormalize_correctly(self):
        """3 fights: weights [0.30, 0.25, 0.20], renormalized to sum=1."""
        fps_scores = [90.0, 80.0, 70.0]
        result = compute_fps_last5(fps_scores)
        raw_weights = [0.30, 0.25, 0.20]
        total = sum(raw_weights)
        norm = [w / total for w in raw_weights]
        expected = sum(fps_scores[i] * norm[i] for i in range(3))
        assert result.fps_last5_avg == pytest.approx(expected, abs=0.1)


# ============================================================
# FCS Tests
# ============================================================

class TestComputeFCS:
    def test_high_confidence_fighter(self):
        """Experienced fighter with good stats."""
        result = compute_fcs(
            fps_last5_avg=75.0,
            fps_last5_n=5,
            win_rate_adjusted=0.80,
            finish_rate=0.60,
            opponent_quality_avg=65.0,
            total_fights=15,
        )
        expected = 75.0 * 0.40 + 80.0 * 0.25 + 60.0 * 0.20 + 65.0 * 0.15
        # = 30 + 20 + 12 + 9.75 = 71.75
        assert result.fcs == pytest.approx(expected, abs=0.1)
        assert result.confidence == "high"

    def test_low_confidence_new_fighter(self):
        """Fighter with 2 fights gets LOW confidence."""
        result = compute_fcs(
            fps_last5_avg=70.0,
            fps_last5_n=2,
            win_rate_adjusted=1.0,
            finish_rate=1.0,
            opponent_quality_avg=30.0,
            total_fights=2,
        )
        assert result.confidence == "low"

    def test_medium_confidence_fighter(self):
        result = compute_fcs(
            fps_last5_avg=65.0,
            fps_last5_n=5,
            win_rate_adjusted=0.70,
            finish_rate=0.40,
            opponent_quality_avg=55.0,
            total_fights=7,
        )
        assert result.confidence == "medium"

    def test_fcs_capped_at_100(self):
        result = compute_fcs(
            fps_last5_avg=100.0,
            fps_last5_n=5,
            win_rate_adjusted=1.0,
            finish_rate=1.0,
            opponent_quality_avg=100.0,
            total_fights=20,
        )
        assert result.fcs <= 100.0


# ============================================================
# Finish Threat Tests
# ============================================================

class TestComputeFinishThreat:
    def test_pure_ko_fighter(self):
        result = compute_finish_threat(ko_wins=8, sub_wins=0, total_fights=10)
        # ko_rate = 0.8, sub_rate = 0.0
        # finish_threat = 0.8 * 0.60 + 0.0 * 0.40 = 0.48
        assert result.finish_threat == pytest.approx(0.48, abs=0.001)
        assert result.confidence == "high"

    def test_pure_sub_fighter(self):
        result = compute_finish_threat(ko_wins=0, sub_wins=6, total_fights=10)
        # sub_rate = 0.6
        # finish_threat = 0.0 * 0.60 + 0.6 * 0.40 = 0.24
        assert result.finish_threat == pytest.approx(0.24, abs=0.001)

    def test_mixed_finisher(self):
        result = compute_finish_threat(ko_wins=4, sub_wins=4, total_fights=10)
        # ko_rate=0.4, sub_rate=0.4
        # = 0.4*0.60 + 0.4*0.40 = 0.24 + 0.16 = 0.40
        assert result.finish_threat == pytest.approx(0.40, abs=0.001)

    def test_low_confidence_under_5_fights(self):
        result = compute_finish_threat(ko_wins=2, sub_wins=1, total_fights=4)
        assert result.confidence == "low"

    def test_capped_at_1(self):
        result = compute_finish_threat(ko_wins=10, sub_wins=10, total_fights=10)
        assert result.finish_threat <= 1.0


# ============================================================
# Volatility Tests
# ============================================================

class TestComputeVolatility:
    def test_consistent_fighter(self):
        """Same FPS every fight = 0 volatility."""
        result = compute_volatility([70.0, 70.0, 70.0, 70.0, 70.0])
        assert result == pytest.approx(0.0, abs=0.01)

    def test_inconsistent_fighter(self):
        """Wide spread in FPS."""
        scores = [40.0, 80.0, 40.0, 80.0, 60.0]
        result = compute_volatility(scores)
        # population std dev
        mean = sum(scores) / len(scores)
        expected = math.sqrt(sum((x - mean) ** 2 for x in scores) / len(scores))
        assert result == pytest.approx(expected, abs=0.01)

    def test_single_fight(self):
        """1 fight = 0 volatility (no variance)."""
        result = compute_volatility([75.0])
        assert result == pytest.approx(0.0, abs=0.01)


# ============================================================
# MMS Tests
# ============================================================

class TestComputeMMS:
    def test_perfectly_matched_stylistic_clash(self):
        """Striker vs grappler at same FCS = maximum MMS."""
        result = compute_mms(
            fcs_a=65.0, fcs_b=65.0,
            finish_threat_a=0.50, finish_threat_b=0.50,
            style_a="striker", style_b="grappler",
            opp_quality_avg_a=65.0, opp_quality_avg_b=65.0,
        )
        # competitiveness = 1.0 (same FCS)
        # action_potential = 0.50
        # style_clash = 0.90 (striker vs grappler)
        # quality_balance = 65/100 = 0.65
        expected = (1.0 * 0.40 + 0.50 * 0.30 + 0.90 * 0.20 + 0.65 * 0.10) * 100
        assert result.mms == pytest.approx(expected, abs=0.1)

    def test_mismatched_fighters(self):
        """Large FCS gap lowers competitiveness."""
        result = compute_mms(
            fcs_a=90.0, fcs_b=30.0,
            finish_threat_a=0.60, finish_threat_b=0.20,
            style_a="all_around", style_b="all_around",
            opp_quality_avg_a=70.0, opp_quality_avg_b=40.0,
        )
        # competitiveness = 1 - 60/100 = 0.40 (poor match)
        assert result.competitiveness == pytest.approx(0.40, abs=0.001)
        assert result.mms < 60  # not a great matchup

    def test_mms_range(self):
        """MMS always 0–100."""
        result = compute_mms(
            fcs_a=100.0, fcs_b=100.0,
            finish_threat_a=1.0, finish_threat_b=1.0,
            style_a="striker", style_b="grappler",
            opp_quality_avg_a=100.0, opp_quality_avg_b=100.0,
        )
        assert 0 <= result.mms <= 100

    def test_style_clash_matrix_symmetric(self):
        """Striker vs grappler = grappler vs striker."""
        assert STYLE_CLASH_MATRIX["striker"]["grappler"] == STYLE_CLASH_MATRIX["grappler"]["striker"]


# ============================================================
# Integration: Full fight scoring pipeline
# ============================================================

class TestScoringPipeline:
    def test_full_fight_pipeline(self):
        """Simulate a 3-round fight where fighter A wins by decision."""
        from app.services.scoring_engine import RoundScoreResult

        # Round stats for fighter A
        stats_r1 = RoundStatsInput(
            sig_strikes_landed=12, sig_strikes_attempted=20,
            takedowns_landed=1, takedown_attempts=2,
            sub_attempts=0, control_time_seconds=60, knockdowns=0,
        )
        stats_r2 = RoundStatsInput(
            sig_strikes_landed=15, sig_strikes_attempted=22,
            takedowns_landed=2, takedown_attempts=3,
            sub_attempts=1, control_time_seconds=120, knockdowns=0,
        )
        stats_r3 = RoundStatsInput(
            sig_strikes_landed=10, sig_strikes_attempted=18,
            takedowns_landed=1, takedown_attempts=2,
            sub_attempts=0, control_time_seconds=90, knockdowns=1,
        )

        rps_r1 = compute_rps(stats_r1)
        rps_r2 = compute_rps(stats_r2)
        rps_r3 = compute_rps(stats_r3)

        # All RPS in valid range
        for rps_result in [rps_r1, rps_r2, rps_r3]:
            assert 0 <= rps_result.rps <= 100

        fps_result = compute_fps(
            [rps_r1, rps_r2, rps_r3],
            scheduled_rounds=3,
            win_method="decision_unanimous",
        )
        assert 0 <= fps_result.fps <= 100
        assert fps_result.result_bonus == 5

        # Career metrics after 5 fights (including this one)
        last5_fps = [fps_result.fps, 68.0, 72.0, 65.0, 70.0]
        rolling = compute_fps_last5(last5_fps)
        assert rolling.confidence == "high"

        fcs_result = compute_fcs(
            fps_last5_avg=rolling.fps_last5_avg,
            fps_last5_n=rolling.n_fights,
            win_rate_adjusted=0.75,
            finish_rate=0.40,
            opponent_quality_avg=58.0,
            total_fights=12,
        )
        assert fcs_result.confidence == "high"
        assert 0 <= fcs_result.fcs <= 100
