-- Migration 002: Add timezone column to users
-- Generated: 2026-04-04

ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Paris';
