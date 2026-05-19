-- Manual migration: run in the Supabase SQL Editor (https://app.supabase.com → SQL Editor).
-- This file is documentation only — it is NOT run by any automated migration tool.

-- Add resume storage to profiles
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS resume_text TEXT,
  ADD COLUMN IF NOT EXISTS resume_filename TEXT;

-- Add match scoring to jobs
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS match_score INTEGER,
  ADD COLUMN IF NOT EXISTS match_reasoning TEXT;
