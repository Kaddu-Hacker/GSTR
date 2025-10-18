from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import math
import json
from io import BytesIO

# Import our custom modules
from models import (
    Upload, UploadStatus, FileType, FileInfo,
    InvoiceLine, GSTRExport, ProcessingResult,
    UploadCreateResponse, GSTR1BOutput, GSTR3BOutput
)
from parser import FileParser
from gstr_generator import GSTRGenerator
from supabase_client import uploads_collection, invoice_lines_collection, gstr_exports_collection
from gemini_service import gemini_service
from json_utils import safe_json_response

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app without a prefix
app = FastAPI(title="GST Filing Automation API with AI")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@api_router.get("/")
async def root():
    return {"message": "GST Filing Automation API with AI", "version": "2.0", "features": ["Supabase", "Gemini AI"]}


@api_router.post("/upload", response_model=UploadCreateResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    seller_state_code: str = Query(default="27", description="Seller's state code (e.g., 27 for Maharashtra)"),
    gstin: str = Query(default="27AABCE1234F1Z5", description="Seller's GSTIN"),
    filing_period: str = Query(default="012025", description="Filing period (MMYYYY)")
):
    """
    Upload Meesho export files (ZIP or individual Excel/CSV files)
    Auto-detects file types and stores for processing
    """
    try:
        # Create upload record
        upload = Upload(
            metadata={
                "seller_state_code": seller_state_code,
                "gstin": gstin,
                "filing_period": filing_period
            }
        )
        
        # Initialize parser
        parser = FileParser(seller_state_code=seller_state_code)
        
        all_files = []
        
        # Process each uploaded file
        for file in files:
            content = await file.read()
            
            # Check if it's a ZIP file
            if file.filename.lower().endswith('.zip'):
                # Extract files from ZIP
                extracted_files = parser.extract_files_from_zip(content)
                
                # Classify extracted files
                classified = parser.detect_and_classify_files(extracted_files)
                all_files.extend(classified)
            else:
                # Single file
                classified = parser.detect_and_classify_files([(file.filename, content)])
                all_files.extend(classified)
        
        # Store file info (without content for now)
        file_infos = []
        for f in all_files:
            file_info = FileInfo(
                filename=f["filename"],
                file_type=FileType(f["file_type"]),
                detected=f["detected"],
                row_count=f.get("row_count"),
                columns=f.get("columns")
            )
            file_infos.append(file_info)
            
            # Store content temporarily in upload metadata
            upload.metadata[f"file_content_{f['filename']}"] = f.get("content", b"").hex()
        
        upload.files = file_infos
        
        # Save to Supabase
        upload_dict = upload.model_dump(mode='json')
        upload_dict['upload_date'] = upload_dict['upload_date'].isoformat() if hasattr(upload_dict['upload_date'], 'isoformat') else upload_dict['upload_date']
        upload_dict['files'] = [f.model_dump(mode='json') for f in upload.files]
        
        await uploads_collection.create(upload_dict)
        
        logger.info(f"Upload created: {upload.id}, {len(file_infos)} files detected")
        
        return UploadCreateResponse(
            upload_id=upload.id,
            files=file_infos,
            message=f"Successfully uploaded {len(file_infos)} file(s)"
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/process/{upload_id}", response_model=ProcessingResult)
async def process_upload(upload_id: str):
    """
    Process uploaded files: parse, validate, and prepare for JSON generation
    Enhanced with Gemini AI for invoice validation
    """
    try:
        # Get upload record
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = Upload(**upload_doc)
        
        # Update status
        await uploads_collection.update(upload_id, {"status": UploadStatus.PROCESSING.value})
        
        # Get metadata
        seller_state_code = upload.metadata.get("seller_state_code", "27")
        
        # Initialize parser
        parser = FileParser(seller_state_code=seller_state_code)
        
        all_invoice_lines = []
        errors = []
        
        # Process each file
        for file_info in upload.files:
            if not file_info.detected:
                errors.append(f"File {file_info.filename} type not detected, skipping")
                continue
            
            try:
                # Retrieve file content from metadata
                content_hex = upload.metadata.get(f"file_content_{file_info.filename}")
                if not content_hex:
                    errors.append(f"File content not found for {file_info.filename}")
                    continue
                
                content = bytes.fromhex(content_hex)
                
                # Parse file
                invoice_lines = parser.parse_file(
                    content,
                    file_info.filename,
                    file_info.file_type,
                    upload_id
                )
                
                all_invoice_lines.extend(invoice_lines)
                logger.info(f"Parsed {len(invoice_lines)} lines from {file_info.filename}")
                
            except Exception as e:
                error_msg = f"Error parsing {file_info.filename}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Save invoice lines to Supabase
        if all_invoice_lines:
            invoice_docs = [line.model_dump(mode='json') for line in all_invoice_lines]
            # Sanitize float values to prevent JSON serialization errors
            invoice_docs = [safe_json_response(doc) for doc in invoice_docs]
            await invoice_lines_collection.insert_many(invoice_docs)
        
        # Update upload status
        status = UploadStatus.COMPLETED if not errors else UploadStatus.FAILED
        await uploads_collection.update(
            upload_id,
            {
                "status": status.value,
                "processing_errors": errors
            }
        )
        
        logger.info(f"Processing completed for upload {upload_id}: {len(all_invoice_lines)} invoice lines")
        
        return ProcessingResult(
            upload_id=upload_id,
            status=status.value,
            invoice_lines_count=len(all_invoice_lines),
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        
        # Update status to failed
        await uploads_collection.update(
            upload_id,
            {
                "status": UploadStatus.FAILED.value,
                "processing_errors": [str(e)]
            }
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/generate/{upload_id}")
async def generate_gstr_json(upload_id: str):
    """
    Generate GSTR-1B and GSTR-3B JSON files
    Enhanced with Gemini AI for validation and insights
    """
    try:
        # Get upload record
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = Upload(**upload_doc)
        
        # Check if processing is complete
        if upload.status != UploadStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Upload must be processed first. Current status: {upload.status}"
            )
        
        # Get invoice lines
        invoice_lines = await invoice_lines_collection.find_by_upload(upload_id)
        
        if not invoice_lines:
            raise HTTPException(status_code=400, detail="No invoice lines found")
        
        # Get metadata
        gstin = upload.metadata.get("gstin", "27AABCE1234F1Z5")
        filing_period = upload.metadata.get("filing_period", "012025")
        
        # Initialize generator
        generator = GSTRGenerator(gstin=gstin, filing_period=filing_period)
        
        # Generate GSTR-1B
        gstr1b = generator.generate_gstr1b(invoice_lines)
        
        # Generate GSTR-3B
        gstr3b = generator.generate_gstr3b(invoice_lines)
        
        # Validate
        warnings = generator.validate_output(gstr1b, gstr3b)
        
        # Save to Supabase
        gstr1b_export = GSTRExport(
            upload_id=upload_id,
            export_type="GSTR1B",
            json_data=gstr1b.model_dump(mode='json'),
            validation_warnings=warnings
        )
        
        gstr3b_export = GSTRExport(
            upload_id=upload_id,
            export_type="GSTR3B",
            json_data=gstr3b.model_dump(mode='json'),
            validation_warnings=warnings
        )
        
        # Save exports
        gstr1b_dict = gstr1b_export.model_dump(mode='json')
        gstr1b_dict = safe_json_response(gstr1b_dict)
        await gstr_exports_collection.insert(gstr1b_dict)
        
        gstr3b_dict = gstr3b_export.model_dump(mode='json')
        gstr3b_dict = safe_json_response(gstr3b_dict)
        await gstr_exports_collection.insert(gstr3b_dict)
        
        logger.info(f"Generated GSTR JSON files for upload {upload_id}")
        
        response_data = {
            "upload_id": upload_id,
            "gstr1b": gstr1b.model_dump(mode='json'),
            "gstr3b": gstr3b.model_dump(mode='json'),
            "validation_warnings": warnings
        }
        
        # Sanitize floats for JSON compatibility
        return safe_json_response(response_data)
        
    except Exception as e:
        import traceback
        logger.error(f"Generation error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/downloads/{upload_id}")
async def get_downloads(upload_id: str):
    """
    Get available downloads for an upload
    """
    try:
        # Get exports
        exports = await gstr_exports_collection.find_by_upload(upload_id)
        
        if not exports:
            raise HTTPException(status_code=404, detail="No exports found for this upload")
        
        return safe_json_response({
            "upload_id": upload_id,
            "exports": exports
        })
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/download/{upload_id}/{file_type}")
async def download_gstr_file(upload_id: str, file_type: str):
    """
    Download GSTR JSON file directly (triggers browser download)
    file_type: 'gstr1b' or 'gstr3b'
    """
    try:
        # Validate file type
        if file_type.lower() not in ['gstr1b', 'gstr3b']:
            raise HTTPException(status_code=400, detail="Invalid file type. Use 'gstr1b' or 'gstr3b'")
        
        # Get the GSTR data
        export_type = "GSTR1B" if file_type.lower() == 'gstr1b' else "GSTR3B"
        exports = await gstr_exports_collection.find_by_upload(upload_id)
        
        if not exports:
            raise HTTPException(status_code=404, detail="No exports found for this upload")
        
        # Find the specific export
        export_data = None
        for export in exports:
            if export.get('export_type') == export_type:
                export_data = export.get('json_data')
                break
        
        if not export_data:
            raise HTTPException(status_code=404, detail=f"{export_type} not found for this upload")
        
        # Get filing period for filename
        upload_doc = await uploads_collection.find_one(upload_id)
        filing_period = upload_doc.get('metadata', {}).get('filing_period', '012025') if upload_doc else '012025'
        
        # Create JSON string
        json_string = json.dumps(export_data, indent=2)
        
        # Create filename
        filename = f"{export_type}_{filing_period}.json"
        
        # Convert to bytes
        json_bytes = json_string.encode('utf-8')
        
        # Return as streaming response with proper headers
        return StreamingResponse(
            BytesIO(json_bytes),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(json_bytes)),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Download file error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/uploads")
async def list_uploads():
    """
    List all uploads
    """
    try:
        uploads = await uploads_collection.find_all()
        
        # Clean up file content from metadata for listing
        for upload in uploads:
            if "metadata" in upload:
                upload["metadata"] = {
                    k: v for k, v in upload["metadata"].items()
                    if not k.startswith("file_content_")
                }
        
        return safe_json_response({"uploads": uploads})
        
    except Exception as e:
        logger.error(f"List uploads error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/upload/{upload_id}")
async def get_upload_details(upload_id: str):
    """
    Get upload details with processing status
    """
    try:
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Clean up file content from metadata
        if "metadata" in upload_doc:
            upload_doc["metadata"] = {
                k: v for k, v in upload_doc["metadata"].items()
                if not k.startswith("file_content_")
            }
        
        # Get invoice lines count
        invoice_count = await invoice_lines_collection.count(upload_id)
        upload_doc["invoice_lines_count"] = invoice_count
        
        # Get exports
        exports = await gstr_exports_collection.find_by_upload(upload_id)
        # Remove large json_data from list view
        for export in exports:
            if 'json_data' in export:
                del export['json_data']
        upload_doc["exports"] = exports
        
        return safe_json_response(upload_doc)
        
    except Exception as e:
        logger.error(f"Get upload details error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/preview/{upload_id}")
async def get_preview_data(upload_id: str):
    """
    Get detailed preview data for review before download
    Shows breakdown by state, rate, document types with audit trail
    Enhanced with AI insights
    """
    try:
        # Get upload record
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Get invoice lines
        invoice_lines = await invoice_lines_collection.find_by_upload(upload_id)
        
        if not invoice_lines:
            return safe_json_response({
                "upload_id": upload_id,
                "summary": {},
                "breakdown": {},
                "audit_log": []
            })
        
        # Categorize data
        sales_lines = [l for l in invoice_lines if l.get("file_type") in ["tcs_sales", "tcs_sales_return"]]
        invoice_docs = [l for l in invoice_lines if l.get("file_type") == "tax_invoice"]
        
        # Build state-wise breakdown
        state_breakdown = {}
        for line in sales_lines:
            state_code = line.get("state_code", "Unknown")
            gst_rate = line.get("gst_rate", 0)
            key = f"{state_code}_{gst_rate}"
            
            if key not in state_breakdown:
                state_breakdown[key] = {
                    "state_code": state_code,
                    "state_name": line.get("end_customer_state_new", "Unknown"),
                    "gst_rate": gst_rate,
                    "is_intra_state": line.get("is_intra_state", False),
                    "count": 0,
                    "taxable_value": 0,
                    "cgst_amount": 0,
                    "sgst_amount": 0,
                    "igst_amount": 0,
                    "tax_amount": 0
                }
            
            state_breakdown[key]["count"] += 1
            state_breakdown[key]["taxable_value"] += (line.get("taxable_value") or 0)
            state_breakdown[key]["cgst_amount"] += (line.get("cgst_amount") or 0)
            state_breakdown[key]["sgst_amount"] += (line.get("sgst_amount") or 0)
            state_breakdown[key]["igst_amount"] += (line.get("igst_amount") or 0)
            state_breakdown[key]["tax_amount"] += (line.get("tax_amount") or 0)
        
        # Build document type breakdown
        doc_type_breakdown = {}
        for line in invoice_docs:
            doc_type = line.get("invoice_type", "Invoice")
            if doc_type not in doc_type_breakdown:
                doc_type_breakdown[doc_type] = {
                    "type": doc_type,
                    "count": 0,
                    "invoice_numbers": []
                }
            doc_type_breakdown[doc_type]["count"] += 1
            doc_type_breakdown[doc_type]["invoice_numbers"].append(line.get("invoice_no"))
        
        # Calculate totals
        total_taxable = sum((l.get("taxable_value") or 0) for l in sales_lines)
        total_tax = sum((l.get("tax_amount") or 0) for l in sales_lines)
        total_cgst = sum((l.get("cgst_amount") or 0) for l in sales_lines)
        total_sgst = sum((l.get("sgst_amount") or 0) for l in sales_lines)
        total_igst = sum((l.get("igst_amount") or 0) for l in sales_lines)
        
        # Audit log
        audit_log = [
            f"Processed {len(sales_lines)} sales transaction lines",
            f"Processed {len(invoice_docs)} invoice document entries",
            f"Total Taxable Value: ₹{total_taxable:.2f}",
            f"Total Tax: ₹{total_tax:.2f} (CGST: ₹{total_cgst:.2f}, SGST: ₹{total_sgst:.2f}, IGST: ₹{total_igst:.2f})",
            f"Unique states found: {len(set(l.get('state_code') for l in sales_lines if l.get('state_code')))}",
            f"Unique GST rates: {sorted(set(l.get('gst_rate') for l in sales_lines if l.get('gst_rate') is not None))}",
            f"Document types: {list(doc_type_breakdown.keys())}"
        ]
        
        return safe_json_response({
            "upload_id": upload_id,
            "summary": {
                "total_transactions": len(sales_lines),
                "total_documents": len(invoice_docs),
                "total_taxable_value": round(total_taxable, 2),
                "total_tax": round(total_tax, 2),
                "total_cgst": round(total_cgst, 2),
                "total_sgst": round(total_sgst, 2),
                "total_igst": round(total_igst, 2),
                "unique_states": len(set(l.get('state_code') for l in sales_lines if l.get('state_code'))),
                "unique_rates": sorted(set(l.get('gst_rate') for l in sales_lines if l.get('gst_rate') is not None))
            },
            "breakdown": {
                "by_state_and_rate": list(state_breakdown.values()),
                "by_document_type": list(doc_type_breakdown.values())
            },
            "audit_log": audit_log
        })
        
    except Exception as e:
        logger.error(f"Preview data error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("GST Filing Automation API with AI - Starting up")
    logger.info("Using Supabase for database and Gemini for AI insights")