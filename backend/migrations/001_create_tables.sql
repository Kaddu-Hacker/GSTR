-- GST Filing Automation Database Schema
-- Creates tables for uploads, invoice_lines, and gstr_exports

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS public.gstr_exports CASCADE;
DROP TABLE IF EXISTS public.invoice_lines CASCADE;
DROP TABLE IF EXISTS public.uploads CASCADE;

-- Create uploads table
CREATE TABLE public.uploads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default_user',
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'uploaded',
    files JSONB DEFAULT '[]'::jsonb,
    processing_errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create invoice_lines table
CREATE TABLE public.invoice_lines (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL,
    file_type TEXT NOT NULL,
    
    -- Original Meesho columns
    gst_rate NUMERIC(10, 2),
    total_taxable_sale_value NUMERIC(15, 2),
    end_customer_state_new TEXT,
    invoice_type TEXT,
    invoice_no TEXT,
    
    -- Computed fields
    state_code TEXT,
    is_return BOOLEAN DEFAULT FALSE,
    taxable_value NUMERIC(15, 2),
    tax_amount NUMERIC(15, 2),
    cgst_amount NUMERIC(15, 2),
    sgst_amount NUMERIC(15, 2),
    igst_amount NUMERIC(15, 2),
    is_intra_state BOOLEAN,
    
    -- Additional fields
    invoice_date TEXT,
    invoice_serial TEXT,
    
    -- Raw data
    raw_data JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Foreign key
    CONSTRAINT fk_upload FOREIGN KEY (upload_id) REFERENCES public.uploads(id) ON DELETE CASCADE
);

-- Create gstr_exports table
CREATE TABLE public.gstr_exports (
    id TEXT PRIMARY KEY,
    upload_id TEXT NOT NULL,
    export_type TEXT NOT NULL,
    export_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    json_data JSONB NOT NULL,
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Foreign key
    CONSTRAINT fk_upload_export FOREIGN KEY (upload_id) REFERENCES public.uploads(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX idx_uploads_user_id ON public.uploads(user_id);
CREATE INDEX idx_uploads_status ON public.uploads(status);
CREATE INDEX idx_uploads_upload_date ON public.uploads(upload_date DESC);

CREATE INDEX idx_invoice_lines_upload_id ON public.invoice_lines(upload_id);
CREATE INDEX idx_invoice_lines_file_type ON public.invoice_lines(file_type);
CREATE INDEX idx_invoice_lines_state_code ON public.invoice_lines(state_code);

CREATE INDEX idx_gstr_exports_upload_id ON public.gstr_exports(upload_id);
CREATE INDEX idx_gstr_exports_export_type ON public.gstr_exports(export_type);

-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE public.uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gstr_exports ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (you can customize these based on your auth requirements)
CREATE POLICY "Allow all operations on uploads" ON public.uploads FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on invoice_lines" ON public.invoice_lines FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on gstr_exports" ON public.gstr_exports FOR ALL USING (true) WITH CHECK (true);

-- Grant permissions to authenticated and service_role
GRANT ALL ON public.uploads TO authenticated, service_role;
GRANT ALL ON public.invoice_lines TO authenticated, service_role;
GRANT ALL ON public.gstr_exports TO authenticated, service_role;

-- Add comments for documentation
COMMENT ON TABLE public.uploads IS 'Stores file upload metadata and processing status';
COMMENT ON TABLE public.invoice_lines IS 'Stores parsed invoice line items from uploaded files';
COMMENT ON TABLE public.gstr_exports IS 'Stores generated GSTR-1B and GSTR-3B JSON outputs';
