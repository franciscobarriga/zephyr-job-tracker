-- Add status column to jobs table
-- Run this in Supabase SQL Editor

-- Add status column with default 'New' for existing rows
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'New';

-- Update any null status to 'New'
UPDATE jobs 
SET status = 'New' 
WHERE status IS NULL;

-- Optional: Add a check constraint for valid statuses
ALTER TABLE jobs 
DROP CONSTRAINT IF EXISTS jobs_status_check;

ALTER TABLE jobs 
ADD CONSTRAINT jobs_status_check 
CHECK (status IN ('New', 'Applied', 'Thinking', 'Ignored'));

-- Verify RLS policies are correct
-- These should already exist, but run to ensure they're set up:

-- Enable RLS
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Users can view their own jobs
DROP POLICY IF EXISTS "Users can view own jobs" ON jobs;
CREATE POLICY "Users can view own jobs" 
ON jobs FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

-- Users can insert their own jobs
DROP POLICY IF EXISTS "Users can insert own jobs" ON jobs;
CREATE POLICY "Users can insert own jobs" 
ON jobs FOR INSERT 
TO authenticated 
WITH CHECK (auth.uid() = user_id);

-- Users can update their own jobs
DROP POLICY IF EXISTS "Users can update own jobs" ON jobs;
CREATE POLICY "Users can update own jobs" 
ON jobs FOR UPDATE 
TO authenticated 
USING (auth.uid() = user_id);

-- Users can delete their own jobs
DROP POLICY IF EXISTS "Users can delete own jobs" ON jobs;
CREATE POLICY "Users can delete own jobs" 
ON jobs FOR DELETE 
TO authenticated 
USING (auth.uid() = user_id);

-- Same for search_configs table
ALTER TABLE search_configs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own search configs" ON search_configs;
CREATE POLICY "Users can view own search configs" 
ON search_configs FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own search configs" ON search_configs;
CREATE POLICY "Users can insert own search configs" 
ON search_configs FOR INSERT 
TO authenticated 
WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own search configs" ON search_configs;
CREATE POLICY "Users can update own search configs" 
ON search_configs FOR UPDATE 
TO authenticated 
USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own search configs" ON search_configs;
CREATE POLICY "Users can delete own search configs" 
ON search_configs FOR DELETE 
TO authenticated 
USING (auth.uid() = user_id);
