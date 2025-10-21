-- GST Filing Automation - Supabase Database Schema V2
-- Schema-driven GSTR-1 with Canonical Models
-- Run this SQL in your Supabase SQL Editor

-- Drop existing tables if you want to recreate (WARNING: This will delete data)
-- DROP TABLE IF EXISTS gstr_exports CASCADE;
-- DROP TABLE IF EXISTS invoice_lines CASCADE;
-- DROP TABLE IF EXISTS uploads CASCADE;

-- 1. Uploads table (enhanced for canonical model)
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT DEFAULT 'default_user',
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'uploaded', -- uploaded, mapping, processing, completed, failed
    files JSONB DEFAULT '[]'::jsonb,
    processing_errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Invoice Lines table (canonical model)
CREATE TABLE IF NOT EXISTS invoice_lines (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    
    -- Core fields
    file_type TEXT,
    origin TEXT, -- 'meesho', 'manual', etc.
    doc_type TEXT, -- 'tax_invoice', 'credit_note', 'debit_note', etc.
    gstr_section TEXT, -- 'b2b', 'b2cs', 'cdnr', etc.
    
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
    
    -- Financial details (stored as numeric for precision)
    taxable_value NUMERIC(15,2),
    gst_rate NUMERIC(5,2),
    
    -- Computed tax (stored as JSONB for flexibility)
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
    
    -- Raw data for audit
    raw_data JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. GSTR Exports table (for GSTR-1 only now)
CREATE TABLE IF NOT EXISTS gstr_exports (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    
    -- Export metadata
    export_type TEXT DEFAULT 'gstr1', -- 'gstr1' only
    export_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    gstin TEXT,
    fp TEXT, -- filing period MMYYYY
    version TEXT DEFAULT '3.1.6',
    
    -- GSTR-1 sections (stored as JSONB)
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
    
    -- Validation and reconciliation
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    validation_errors JSONB DEFAULT '[]'::jsonb,
    reconciliation_report JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Document Ranges table (for Table 13)
CREATE TABLE IF NOT EXISTS document_ranges (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_uploads_upload_date ON uploads(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);

CREATE INDEX IF NOT EXISTS idx_invoice_lines_upload_id ON invoice_lines(upload_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_gstr_section ON invoice_lines(gstr_section);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_doc_type ON invoice_lines(doc_type);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_no ON invoice_lines(invoice_no_norm);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_gstin ON invoice_lines(gstin_uin);

CREATE INDEX IF NOT EXISTS idx_gstr_exports_upload_id ON gstr_exports(upload_id);
CREATE INDEX IF NOT EXISTS idx_gstr_exports_export_type ON gstr_exports(export_type);
CREATE INDEX IF NOT EXISTS idx_gstr_exports_gstin ON gstr_exports(gstin);

CREATE INDEX IF NOT EXISTS idx_document_ranges_upload_id ON document_ranges(upload_id);
CREATE INDEX IF NOT EXISTS idx_document_ranges_doc_type ON document_ranges(doc_type);

-- Add updated_at trigger for uploads
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

-- Enable Row Level Security (RLS)
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE gstr_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_ranges ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Enable all access for service role" ON uploads;
DROP POLICY IF EXISTS "Enable all access for service role" ON invoice_lines;
DROP POLICY IF EXISTS "Enable all access for service role" ON gstr_exports;
DROP POLICY IF EXISTS "Enable all access for service role" ON document_ranges;

-- Create policies for service role access (allows backend to access all rows)
CREATE POLICY "Enable all access for service role" ON uploads FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON invoice_lines FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON gstr_exports FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON document_ranges FOR ALL USING (true);

-- Grant permissions
GRANT ALL ON uploads TO service_role;
GRANT ALL ON invoice_lines TO service_role;
GRANT ALL ON gstr_exports TO service_role;
GRANT ALL ON document_ranges TO service_role;

-- Create a view for quick summary statistics
CREATE OR REPLACE VIEW upload_summary AS
SELECT 
    u.id,
    u.upload_date,
    u.status,
    COUNT(DISTINCT il.id) as invoice_count,
    COUNT(DISTINCT ge.id) as export_count,
    SUM(il.taxable_value) as total_taxable_value
FROM uploads u
LEFT JOIN invoice_lines il ON u.id = il.upload_id
LEFT JOIN gstr_exports ge ON u.id = ge.upload_id
GROUP BY u.id, u.upload_date, u.status;

GRANT SELECT ON upload_summary TO service_role;
