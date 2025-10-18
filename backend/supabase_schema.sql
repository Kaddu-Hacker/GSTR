-- GST Filing Automation - Supabase Database Schema
-- Run this SQL in your Supabase SQL Editor to create tables

-- 1. Uploads table
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT DEFAULT 'default_user',
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'uploaded',
    files JSONB DEFAULT '[]'::jsonb,
    processing_errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Invoice Lines table
CREATE TABLE IF NOT EXISTS invoice_lines (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    file_type TEXT,
    gst_rate NUMERIC,
    total_taxable_sale_value NUMERIC,
    end_customer_state_new TEXT,
    invoice_type TEXT,
    invoice_no TEXT,
    state_code TEXT,
    is_return BOOLEAN DEFAULT FALSE,
    taxable_value NUMERIC,
    tax_amount NUMERIC,
    cgst_amount NUMERIC,
    sgst_amount NUMERIC,
    igst_amount NUMERIC,
    is_intra_state BOOLEAN,
    invoice_date TEXT,
    invoice_serial TEXT,
    raw_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. GSTR Exports table
CREATE TABLE IF NOT EXISTS gstr_exports (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    export_type TEXT,
    export_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    json_data JSONB DEFAULT '{}'::jsonb,
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_uploads_upload_date ON uploads(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_upload_id ON invoice_lines(upload_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_file_type ON invoice_lines(file_type);
CREATE INDEX IF NOT EXISTS idx_gstr_exports_upload_id ON gstr_exports(upload_id);
CREATE INDEX IF NOT EXISTS idx_gstr_exports_export_type ON gstr_exports(export_type);

-- Add updated_at trigger for uploads
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_uploads_updated_at BEFORE UPDATE ON uploads
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE gstr_exports ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (allows backend to access all rows)
CREATE POLICY "Enable all access for service role" ON uploads FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON invoice_lines FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON gstr_exports FOR ALL USING (true);

-- Grant permissions
GRANT ALL ON uploads TO service_role;
GRANT ALL ON invoice_lines TO service_role;
GRANT ALL ON gstr_exports TO service_role;
