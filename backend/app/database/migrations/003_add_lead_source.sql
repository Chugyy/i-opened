-- Migration 003: Add source tracking columns to leads
-- Allows identifying where a lead came from (landing page, ad, etc.)

ALTER TABLE leads ADD COLUMN IF NOT EXISTS source VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_source VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_medium VARCHAR(100);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS utm_campaign VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
