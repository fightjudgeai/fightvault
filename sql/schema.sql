-- =============================================================
-- FightVault — Fighter Database & Archive
-- Supabase / PostgreSQL Schema v1.0
-- Run this in Supabase SQL editor (in order)
-- =============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================
-- ENUMS
-- =============================================================

CREATE TYPE fighting_style AS ENUM ('striker', 'grappler', 'wrestler', 'all_around', 'unknown');
CREATE TYPE fight_result AS ENUM ('win', 'loss', 'draw', 'no_contest', 'pending');
CREATE TYPE win_method AS ENUM ('ko_tko', 'submission', 'decision_unanimous', 'decision_split', 'decision_majority', 'dq', 'no_contest', 'pending');
CREATE TYPE weight_class AS ENUM (
  'atomweight', 'strawweight', 'flyweight', 'bantamweight', 'featherweight',
  'lightweight', 'welterweight', 'middleweight', 'light_heavyweight', 'heavyweight',
  'super_heavyweight', 'catch_weight', 'open_weight'
);
CREATE TYPE event_status AS ENUM ('draft', 'confirmed', 'completed', 'cancelled');
CREATE TYPE confidence_level AS ENUM ('low', 'medium', 'high');
CREATE TYPE log_action AS ENUM (
  'fighter_created', 'fighter_updated',
  'fight_created', 'fight_updated', 'fight_result_set',
  'round_stats_submitted',
  'scores_computed'
);

-- =============================================================
-- PROMOTIONS (minimal — FK anchor for fighters/events)
-- =============================================================

CREATE TABLE promotions (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  logo_url    TEXT,
  website     TEXT,
  description TEXT,
  city        TEXT,
  state       TEXT,
  country     TEXT DEFAULT 'US',
  active      BOOLEAN NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_promotions_slug ON promotions(slug);
CREATE INDEX idx_promotions_active ON promotions(active);

-- =============================================================
-- EVENTS (minimal — FK anchor for bouts)
-- =============================================================

CREATE TABLE events (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  promotion_id  UUID REFERENCES promotions(id) ON DELETE SET NULL,
  name          TEXT NOT NULL,
  event_date    DATE,
  status        event_status NOT NULL DEFAULT 'draft',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_date ON events(event_date DESC);

-- =============================================================
-- FIGHTERS
-- =============================================================

CREATE TABLE fighters (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  promotion_id          UUID REFERENCES promotions(id) ON DELETE SET NULL,
  first_name            TEXT NOT NULL,
  last_name             TEXT NOT NULL,
  nickname              TEXT,
  weight_class          weight_class NOT NULL,
  fighting_style        fighting_style NOT NULL DEFAULT 'unknown',
  date_of_birth         DATE,
  nationality           TEXT,
  gym                   TEXT,
  -- Record (tracked from bouts, also manually seeded)
  wins                  INT NOT NULL DEFAULT 0,
  losses                INT NOT NULL DEFAULT 0,
  draws                 INT NOT NULL DEFAULT 0,
  no_contests           INT NOT NULL DEFAULT 0,
  -- Finish breakdown (source of truth for career metrics)
  ko_tko_wins           INT NOT NULL DEFAULT 0,
  submission_wins       INT NOT NULL DEFAULT 0,
  -- External IDs for deduplication
  sherdog_id            TEXT,
  tapology_id           TEXT,
  ufc_stats_id          TEXT,
  -- Meta
  is_active             BOOLEAN NOT NULL DEFAULT true,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fighters_name_trgm ON fighters USING GIN ((first_name || ' ' || last_name) gin_trgm_ops);
CREATE INDEX idx_fighters_promotion ON fighters(promotion_id);
CREATE INDEX idx_fighters_weight_class ON fighters(weight_class);

COMMENT ON TYPE weight_class IS
  'atomweight=105, strawweight=115, flyweight=125, bantamweight=135, featherweight=145, lightweight=155, welterweight=170, middleweight=185, light_heavyweight=205, heavyweight=265';

-- =============================================================
-- BOUTS (individual fights)
-- =============================================================

CREATE TABLE bouts (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id          UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  bout_order        INT NOT NULL,
  fighter_a_id      UUID NOT NULL REFERENCES fighters(id),
  fighter_b_id      UUID NOT NULL REFERENCES fighters(id),
  weight_class      weight_class NOT NULL,
  scheduled_rounds  INT NOT NULL DEFAULT 3,
  is_title_fight    BOOLEAN NOT NULL DEFAULT false,
  -- Result (filled post-fight)
  result_fighter_a  fight_result NOT NULL DEFAULT 'pending',
  result_fighter_b  fight_result NOT NULL DEFAULT 'pending',
  win_method        win_method NOT NULL DEFAULT 'pending',
  end_round         INT,
  end_time_seconds  INT,
  actual_rounds     INT,
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT different_fighters CHECK (fighter_a_id != fighter_b_id)
);

CREATE INDEX idx_bouts_event ON bouts(event_id);
CREATE INDEX idx_bouts_fighter_a ON bouts(fighter_a_id);
CREATE INDEX idx_bouts_fighter_b ON bouts(fighter_b_id);

-- =============================================================
-- ROUND STATS (append-only source of truth)
-- =============================================================

CREATE TABLE round_stats (
  id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bout_id                 UUID NOT NULL REFERENCES bouts(id) ON DELETE CASCADE,
  round_number            INT NOT NULL,
  fighter_id              UUID NOT NULL REFERENCES fighters(id),
  -- Striking
  sig_strikes_landed      INT NOT NULL DEFAULT 0,
  sig_strikes_attempted   INT NOT NULL DEFAULT 0,
  total_strikes_landed    INT NOT NULL DEFAULT 0,
  total_strikes_attempted INT NOT NULL DEFAULT 0,
  -- Grappling
  takedowns_landed        INT NOT NULL DEFAULT 0,
  takedown_attempts       INT NOT NULL DEFAULT 0,
  sub_attempts            INT NOT NULL DEFAULT 0,
  reversals               INT NOT NULL DEFAULT 0,
  -- Control
  control_time_seconds    INT NOT NULL DEFAULT 0,
  knockdowns              INT NOT NULL DEFAULT 0,
  -- Judge scores (optional)
  judge1_score            INT,
  judge2_score            INT,
  judge3_score            INT,
  -- Meta
  submitted_by            UUID,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT valid_round CHECK (round_number >= 1 AND round_number <= 12),
  CONSTRAINT valid_control CHECK (control_time_seconds >= 0 AND control_time_seconds <= 300),
  UNIQUE(bout_id, round_number, fighter_id)
);

CREATE INDEX idx_round_stats_bout ON round_stats(bout_id);
CREATE INDEX idx_round_stats_fighter ON round_stats(fighter_id);

-- =============================================================
-- COMPUTED SCORES (derived — never overwrite raw stats)
-- =============================================================

-- Per-round computed scores
CREATE TABLE round_scores (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  round_stats_id  UUID NOT NULL REFERENCES round_stats(id) ON DELETE CASCADE,
  bout_id         UUID NOT NULL REFERENCES bouts(id),
  fighter_id      UUID NOT NULL REFERENCES fighters(id),
  round_number    INT NOT NULL,
  striking_eff    NUMERIC(5,4) NOT NULL,
  grappling_eff   NUMERIC(5,4) NOT NULL,
  control_dom     NUMERIC(5,4) NOT NULL,
  finish_threat   NUMERIC(5,4) NOT NULL,
  rps             NUMERIC(6,2) NOT NULL,
  computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-fight computed scores
CREATE TABLE fight_scores (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  bout_id             UUID NOT NULL REFERENCES bouts(id) ON DELETE CASCADE,
  fighter_id          UUID NOT NULL REFERENCES fighters(id),
  fps_base            NUMERIC(6,2) NOT NULL,
  result_bonus        NUMERIC(4,1) NOT NULL DEFAULT 0,
  fps                 NUMERIC(6,2) NOT NULL,
  finish_threat       NUMERIC(5,4),
  opponent_fcs        NUMERIC(6,2),
  computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(bout_id, fighter_id)
);

CREATE INDEX idx_fight_scores_fighter ON fight_scores(fighter_id);
CREATE INDEX idx_fight_scores_bout ON fight_scores(bout_id);

-- Per-fighter career snapshot (recomputed on each new fight)
CREATE TABLE fighter_career_scores (
  id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  fighter_id            UUID NOT NULL REFERENCES fighters(id) ON DELETE CASCADE,
  fps_last5_avg         NUMERIC(6,2),
  fps_last5_n           INT NOT NULL DEFAULT 0,
  fps_last5_confidence  confidence_level NOT NULL DEFAULT 'low',
  win_rate_adjusted     NUMERIC(5,4),
  finish_rate           NUMERIC(5,4),
  opponent_quality_avg  NUMERIC(6,2),
  fcs                   NUMERIC(6,2),
  fcs_confidence        confidence_level NOT NULL DEFAULT 'low',
  volatility_score      NUMERIC(6,2),
  finish_threat         NUMERIC(5,4),
  total_fights          INT NOT NULL DEFAULT 0,
  computed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(fighter_id)
);

CREATE INDEX idx_fighter_career_scores_fighter ON fighter_career_scores(fighter_id);
CREATE INDEX idx_fighter_career_scores_fcs ON fighter_career_scores(fcs DESC NULLS LAST);

-- =============================================================
-- OPERATOR AUDIT LOG (append-only)
-- =============================================================

CREATE TABLE operator_logs (
  id          BIGSERIAL PRIMARY KEY,
  user_id     UUID,
  action      log_action NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id   UUID,
  payload     JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_operator_logs_entity ON operator_logs(entity_type, entity_id);

-- =============================================================
-- ROW LEVEL SECURITY (enable after Supabase auth setup)
-- =============================================================

-- ALTER TABLE fighters ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE bouts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE round_stats ENABLE ROW LEVEL SECURITY;
