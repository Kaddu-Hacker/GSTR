# \ud83d\ude80 GST Filing Automation with AI

> **AI-Powered GST Filing** for Meesho Sellers with Gemini AI validation and Supabase database

![Version](https://img.shields.io/badge/version-2.0-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110.1-green)
![React](https://img.shields.io/badge/React-19.0-blue)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)
![Gemini](https://img.shields.io/badge/Gemini-AI-orange)

A comprehensive web application for automating GST filing for Meesho sellers. Upload Meesho export files and automatically generate portal-ready GSTR-1B and GSTR-3B JSON files with AI-powered validation.

## Features

### Core Functionality
- **File Upload**: Support for ZIP archives or individual Excel/CSV files
- **Auto-Detection**: Automatically identifies TCS sales, sales returns, and tax invoice files
- **Data Processing**: 
  - Parses Meesho export columns
  - Normalizes state codes
  - Computes tax splits (CGST/SGST/IGST)
  - Handles returns as negative values
- **GSTR Generation**: Produces portal-ready JSON files for:
  - GSTR-1B (Tables 7, 13, 14)
  - GSTR-3B (Section 3.1)
- **Validation**: Reconciles data between GSTR-1B and GSTR-3B
- **Upload History**: Track and retrieve previous uploads

### GSTR Tables Generated

#### GSTR-1B
- **Table 7 (B2C Others)**: Unregistered buyers grouped by state and GST rate
- **Table 13 (Documents Issued)**: Invoice serial ranges with missing number detection
- **Table 14 (ECO Supplies)**: E-commerce operator (Meesho) aggregated supplies

#### GSTR-3B
- **Section 3.1**: Outward taxable supplies summary

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: MongoDB
- **Excel Parsing**: pandas + openpyxl
- **Decimal Math**: Python Decimal for precise tax calculations

### Frontend
- **Framework**: React 19
- **Styling**: Tailwind CSS + shadcn/ui
- **HTTP Client**: Axios

## Usage

### 1. Configure GST Details
- GSTIN (e.g., `27AABCE1234F1Z5`)
- State Code (e.g., `27` for Maharashtra)
- Filing Period (e.g., `012025` for January 2025)

### 2. Upload Files
Upload Meesho export files:
- `tcs_sales.xlsx`
- `tcs_sales_return.xlsx`
- `Tax_invoice_details.xlsx`

Or upload as a single ZIP archive.

### 3. Automatic Processing
The app automatically:
1. Detects file types
2. Parses and validates data
3. Generates GSTR JSON files

### 4. Download Results
Download portal-ready JSON files for GSTR-1B and GSTR-3B.

## Testing

Generate sample test files:
```bash
python scripts/generate_sample_data.py
```

This creates sample Meesho export files in `/app/test_data/`

## API Endpoints

- `POST /api/upload` - Upload files
- `POST /api/process/{upload_id}` - Process uploaded files
- `POST /api/generate/{upload_id}` - Generate GSTR JSON
- `GET /api/downloads/{upload_id}` - Get generated files
- `GET /api/uploads` - List all uploads
- `GET /api/upload/{upload_id}` - Get upload details

---

**Made with ❤️ using Emergent**