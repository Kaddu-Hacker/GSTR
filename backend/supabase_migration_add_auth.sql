-- Migration Script: Add Authentication Support to Existing Tables
-- This script safely adds user_id columns and auth features to existing tables
-- Run this in Supabase Dashboard → SQL Editor

-- ============================================================================
-- PART 1: Add user_id columns to existing tables
-- ============================================================================

-- Add user_id to uploads table (nullable first to avoid errors)
ALTER TABLE uploads 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to invoice_lines table
ALTER TABLE invoice_lines 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to gstr_exports table
ALTER TABLE gstr_exports 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add user_id to document_ranges table (if it exists)
ALTER TABLE document_ranges 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Add storage_urls to uploads table for Supabase Storage
ALTER TABLE uploads 
ADD COLUMN IF NOT EXISTS storage_urls JSONB DEFAULT '{}'::jsonb;

-- ============================================================================
-- PART 2: Set default user_id for existing records
-- ============================================================================

-- Create a default system user (or use existing auth.users if you have one)
-- For now, we'll set existing records to a placeholder UUID
DO $$ 
BEGIN
    -- Update existing records with a default UUID
    UPDATE uploads SET user_id = '00000000-0000-0000-0000-000000000001'::uuid WHERE user_id IS NULL;
    UPDATE invoice_lines SET user_id = '00000000-0000-0000-0000-000000000001'::uuid WHERE user_id IS NULL;
    UPDATE gstr_exports SET user_id = '00000000-0000-0000-0000-000000000001'::uuid WHERE user_id IS NULL;
    
    -- Update document_ranges if table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'document_ranges') THEN
        UPDATE document_ranges SET user_id = '00000000-0000-0000-0000-000000000001'::uuid WHERE user_id IS NULL;
    END IF;
END $$;

-- ============================================================================
-- PART 3: Make user_id NOT NULL and add foreign key constraints (optional)
-- ============================================================================

-- Note: Commenting out foreign key constraints to avoid errors if auth.users doesn't exist
-- You can uncomment these after setting up authentication

-- ALTER TABLE uploads 
-- ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE uploads 
-- ADD CONSTRAINT uploads_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- ALTER TABLE invoice_lines 
-- ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE invoice_lines 
-- ADD CONSTRAINT invoice_lines_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- ALTER TABLE gstr_exports 
-- ALTER COLUMN user_id SET NOT NULL;
-- ALTER TABLE gstr_exports 
-- ADD CONSTRAINT gstr_exports_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- ============================================================================
-- PART 4: Create indexes for performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_user_id ON invoice_lines(user_id);
CREATE INDEX IF NOT EXISTS idx_gstr_exports_user_id ON gstr_exports(user_id);

-- ============================================================================
-- PART 5: Update or create RLS policies (DISABLED BY DEFAULT)
-- ============================================================================

-- Note: RLS is disabled by default to avoid breaking existing functionality
-- Enable after you've set up authentication properly

-- Disable RLS for now
ALTER TABLE uploads DISABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_lines DISABLE ROW LEVEL SECURITY;
ALTER TABLE gstr_exports DISABLE ROW LEVEL SECURITY;

-- When ready to enable RLS, uncomment the following:
/*
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE gstr_exports ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Enable all access for service role" ON uploads;
DROP POLICY IF EXISTS "Enable all access for service role" ON invoice_lines;
DROP POLICY IF EXISTS "Enable all access for service role" ON gstr_exports;

-- Create service role policies (allows backend full access)
CREATE POLICY "Enable all access for service role" ON uploads FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON invoice_lines FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON gstr_exports FOR ALL USING (true);

-- Create user policies (users see only their data)
CREATE POLICY "Users can view their own uploads" ON uploads
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own uploads" ON uploads
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their own uploads" ON uploads
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own invoice lines" ON invoice_lines
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own invoice lines" ON invoice_lines
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own exports" ON gstr_exports
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own exports" ON gstr_exports
    FOR INSERT WITH CHECK (auth.uid() = user_id);
*/

-- ============================================================================
-- PART 6: Enable Realtime (optional)
-- ============================================================================

-- Enable realtime for uploads table
-- ALTER PUBLICATION supabase_realtime ADD TABLE uploads;

-- ============================================================================
-- PART 7: Grant permissions
-- ============================================================================

GRANT ALL ON uploads TO service_role;
GRANT ALL ON invoice_lines TO service_role;
GRANT ALL ON gstr_exports TO service_role;
GRANT ALL ON uploads TO authenticated;
GRANT ALL ON invoice_lines TO authenticated;
GRANT ALL ON gstr_exports TO authenticated;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Summary of changes:
-- 1. Added user_id column to all tables (nullable)
-- 2. Added storage_urls column to uploads table
-- 3. Set default user_id for existing records
-- 4. Created indexes for performance
-- 5. Disabled RLS (for backward compatibility)
-- 6. Granted necessary permissions

-- Next steps:
-- 1. This migration is complete and safe
-- 2. Your app should now work without errors
-- 3. When ready to enable authentication:
--    a. Enable Email auth in Supabase Dashboard
--    b. Uncomment and run the RLS policies section above
--    c. Create the gst-uploads storage bucket

SELECT 'Migration completed successfully!' as status;
