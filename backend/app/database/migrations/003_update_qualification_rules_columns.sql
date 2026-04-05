-- Migration 003: Update qualification_rules to match CRUD schema
-- Replaces old (operator, threshold_value) with (disqualify_values, min_length, contains_keywords, min_value)

ALTER TABLE qualification_rules
    DROP COLUMN IF EXISTS operator,
    DROP COLUMN IF EXISTS threshold_value,
    ADD COLUMN IF NOT EXISTS disqualify_values JSONB,
    ADD COLUMN IF NOT EXISTS min_length INTEGER,
    ADD COLUMN IF NOT EXISTS contains_keywords JSONB,
    ADD COLUMN IF NOT EXISTS min_value NUMERIC;

DROP INDEX IF EXISTS idx_qualification_rules_operator;
