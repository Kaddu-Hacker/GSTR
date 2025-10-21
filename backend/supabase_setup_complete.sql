-- GST Filing Automation - Complete Supabase Setup
-- Includes Auth, Storage, RLS, and Realtime
-- Run this SQL in your Supabase SQL Editor

-- ============================================================================
-- PART 1: CORE TABLES WITH AUTH INTEGRATION
-- ============================================================================

-- 1. Uploads table (with proper user authentication)
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'uploaded',
    files JSONB DEFAULT '[]'::jsonb,
    processing_errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    storage_urls JSONB DEFAULT '{}'::jsonb,  -- Store file URLs from Supabase Storage
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Invoice Lines table (canonical model)
CREATE TABLE IF NOT EXISTS invoice_lines (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Core fields
    file_type TEXT,
    origin TEXT,
    doc_type TEXT,
    gstr_section TEXT,
    
    -- Buyer/Seller info
    gstin_uin TEXT,
    place_of_supply TEXT,
    place_of_supply_code TEXT,
    
    -- Invoice details
    invoice_no_raw TEXT,
    invoice_no_norm TEXT,
    invoice_date TEXT,
    invoice_prefix TEXT,
    invoice_serial INTEGER,
    
    -- Financial details
    taxable_value NUMERIC(15,2),
    gst_rate NUMERIC(5,2),
    computed_tax JSONB DEFAULT '{}'::jsonb,
    
    -- HSN details
    hsn_code TEXT,
    description TEXT,
    uqc TEXT,
    quantity NUMERIC(15,3),
    
    -- Flags
    is_reverse_charge BOOLEAN DEFAULT FALSE,
    is_return BOOLEAN DEFAULT FALSE,
    is_intra_state BOOLEAN,
    
    -- Raw data
    raw_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. GSTR Exports table
CREATE TABLE IF NOT EXISTS gstr_exports (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    export_type TEXT DEFAULT 'gstr1',
    export_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    gstin TEXT,
    fp TEXT,
    version TEXT DEFAULT '3.1.6',
    
    -- GSTR-1 sections
    b2b JSONB DEFAULT '[]'::jsonb,
    b2cl JSONB DEFAULT '[]'::jsonb,
    b2cs JSONB DEFAULT '[]'::jsonb,
    cdnr JSONB DEFAULT '[]'::jsonb,
    cdnur JSONB DEFAULT '[]'::jsonb,
    exp JSONB DEFAULT '[]'::jsonb,
    at JSONB DEFAULT '[]'::jsonb,
    atadj JSONB DEFAULT '[]'::jsonb,
    hsn JSONB DEFAULT '[]'::jsonb,
    doc_iss JSONB DEFAULT '[]'::jsonb,
    
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    validation_errors JSONB DEFAULT '[]'::jsonb,
    reconciliation_report JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Document Ranges table
CREATE TABLE IF NOT EXISTS document_ranges (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    doc_type TEXT NOT NULL,
    doc_prefix TEXT,
    doc_from TEXT,
    doc_to TEXT,
    from_serial INTEGER,
    to_serial INTEGER,
    found_count INTEGER,
    cancelled_count INTEGER,
    cancelled_serials JSONB DEFAULT '[]'::jsonb,
    is_sequential BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- PART 2: INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_uploads_upload_date ON uploads(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);

CREATE INDEX IF NOT EXISTS idx_invoice_lines_upload_id ON invoice_lines(upload_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_user_id ON invoice_lines(user_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_gstr_section ON invoice_lines(gstr_section);

CREATE INDEX IF NOT EXISTS idx_gstr_exports_upload_id ON gstr_exports(upload_id);
CREATE INDEX IF NOT EXISTS idx_gstr_exports_user_id ON gstr_exports(user_id);

CREATE INDEX IF NOT EXISTS idx_document_ranges_upload_id ON document_ranges(upload_id);
CREATE INDEX IF NOT EXISTS idx_document_ranges_user_id ON document_ranges(user_id);

-- ============================================================================
-- PART 3: TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_uploads_updated_at ON uploads;
CREATE TRIGGER update_uploads_updated_at BEFORE UPDATE ON uploads
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 4: ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE gstr_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_ranges ENABLE ROW LEVEL SECURITY;

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view their own uploads" ON uploads;
DROP POLICY IF EXISTS "Users can insert their own uploads" ON uploads;
DROP POLICY IF EXISTS "Users can update their own uploads" ON uploads;
DROP POLICY IF EXISTS "Users can delete their own uploads" ON uploads;
DROP POLICY IF EXISTS "Service role has full access to uploads" ON uploads;

DROP POLICY IF EXISTS "Users can view their own invoice lines" ON invoice_lines;
DROP POLICY IF EXISTS "Users can insert their own invoice lines" ON invoice_lines;
DROP POLICY IF EXISTS "Service role has full access to invoice_lines" ON invoice_lines;

DROP POLICY IF EXISTS "Users can view their own exports" ON gstr_exports;
DROP POLICY IF EXISTS "Users can insert their own exports" ON gstr_exports;
DROP POLICY IF EXISTS "Service role has full access to gstr_exports" ON gstr_exports;

DROP POLICY IF EXISTS "Users can view their own document ranges" ON document_ranges;
DROP POLICY IF EXISTS "Users can insert their own document ranges" ON document_ranges;
DROP POLICY IF EXISTS "Service role has full access to document_ranges" ON document_ranges;

-- Uploads policies
CREATE POLICY "Users can view their own uploads" ON uploads
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own uploads" ON uploads
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own uploads" ON uploads
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own uploads" ON uploads
    FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to uploads" ON uploads
    FOR ALL USING (true);

-- Invoice lines policies
CREATE POLICY "Users can view their own invoice lines" ON invoice_lines
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own invoice lines" ON invoice_lines
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access to invoice_lines" ON invoice_lines
    FOR ALL USING (true);

-- GSTR exports policies
CREATE POLICY "Users can view their own exports" ON gstr_exports
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own exports" ON gstr_exports
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access to gstr_exports" ON gstr_exports
    FOR ALL USING (true);

-- Document ranges policies
CREATE POLICY "Users can view their own document ranges" ON document_ranges
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own document ranges" ON document_ranges
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access to document_ranges" ON document_ranges
    FOR ALL USING (true);

-- ============================================================================
-- PART 5: STORAGE BUCKET SETUP (Run in SQL, then configure in Storage UI)
-- ============================================================================

-- Note: Storage bucket creation is done through Supabase Dashboard > Storage
-- Create a bucket named 'gst-uploads' with the following settings:
-- - Public: false (private)
-- - File size limit: 50MB
-- - Allowed MIME types: application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/zip

-- Storage policies (run after creating bucket)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('gst-uploads', 'gst-uploads', false) ON CONFLICT DO NOTHING;

-- ============================================================================
-- PART 6: REALTIME ENABLEMENT
-- ============================================================================

-- Enable realtime for uploads table (for live status updates)
ALTER PUBLICATION supabase_realtime ADD TABLE uploads;

-- ============================================================================
-- PART 7: HELPER VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW upload_summary AS
SELECT 
    u.id,
    u.user_id,
    u.upload_date,
    u.status,
    COUNT(DISTINCT il.id) as invoice_count,
    COUNT(DISTINCT ge.id) as export_count,
    SUM(il.taxable_value) as total_taxable_value
FROM uploads u
LEFT JOIN invoice_lines il ON u.id = il.upload_id
LEFT JOIN gstr_exports ge ON u.id = ge.upload_id
GROUP BY u.id, u.user_id, u.upload_date, u.status;

GRANT SELECT ON upload_summary TO authenticated;
GRANT SELECT ON upload_summary TO service_role;

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================

-- Next steps:
-- 1. Go to Supabase Dashboard > Storage > Create new bucket 'gst-uploads'
-- 2. Set bucket to private and configure file size limits
-- 3. Enable Email Auth in Authentication > Providers
-- 4. Optionally enable Google OAuth for social login
