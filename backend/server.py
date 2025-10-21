"""
Enhanced GST Filing Automation API - Schema-Driven GSTR-1 Only
Removes GSTR-3B, adds auto-mapping, canonical data models, and enhanced validation
"""

from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query, Body, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import json
from io import BytesIO

# Import canonical models
from models_canonical import (
    Upload, UploadStatus, FileType, FileInfo,
    CanonicalInvoiceLine, DocumentRange, GSTR1Export,
    ProcessingResult, UploadCreateResponse, HeaderMapping,
    MappingTemplate
)
from parser_enhanced import EnhancedFileParser
from gstr1_generator_schema_driven import SchemaDriverGSTR1Generator
from gstr1_complete_generator import CompleteGSTR1Generator
from invoice_range_detector import InvoiceRangeDetector
from auto_mapper import HeaderMatcher, create_meesho_mapping_template
from gemini_service import gemini_service

# Use MongoDB client (fallback when Supabase not configured)
try:
    from supabase_client_enhanced import (
        uploads_collection, invoice_lines_collection, gstr_exports_collection,
        document_ranges_collection, storage, auth
    )
    logger.info("✅ Using Supabase client")
except Exception as e:
    logger.warning(f"⚠️ Supabase not available, using MongoDB: {e}")
    from mongo_client import (
        uploads_collection, invoice_lines_collection, gstr_exports_collection,
        document_ranges_collection, storage, auth
    )
from json_utils import safe_json_response
from auth_middleware import get_current_user, get_current_user_optional
import auth_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI(title="GST Filing Automation API - GSTR-1 Schema-Driven")

# Create router with /api prefix
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
    return {
        "message": "GST Filing Automation API - Schema-Driven GSTR-1 with Supabase",
        "version": "3.0",
        "features": [
            "Supabase Auth", 
            "Supabase Storage",
            "Supabase Realtime",
            "Decimal Precision", 
            "Auto-Mapping", 
            "All GSTR-1 Sections", 
            "Portal-Compliant"
        ]
    }


@api_router.post("/upload", response_model=UploadCreateResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    seller_state_code: str = Query(default="27"),
    gstin: str = Query(default="27AABCE1234F1Z5"),
    filing_period: str = Query(default="012025"),
    use_gemini: bool = Query(default=True),
    current_user = Depends(get_current_user_optional)
):
    """
    Upload files with Gemini AI-powered auto-detection and mapping suggestions
    Uses Supabase Storage for file storage + Gemini for intelligent file analysis
    """
    try:
        # Get user ID (use default UUID if not authenticated for backward compatibility)
        user_id = str(current_user.id) if current_user else "00000000-0000-0000-0000-000000000001"
        
        upload = Upload(
            metadata={
                "seller_state_code": seller_state_code,
                "gstin": gstin,
                "filing_period": filing_period,
                "use_gemini": use_gemini
            }
        )
        
        parser = EnhancedFileParser(seller_state_code=seller_state_code)
        all_files = []
        needs_mapping = False
        storage_urls = {}
        gemini_file_insights = {}
        
        # Process each uploaded file
        for file in files:
            content = await file.read()
            
            # Upload to Supabase Storage
            content_type = file.content_type or "application/octet-stream"
            storage_path = f"{upload.id}/{file.filename}"
            
            try:
                storage_result = storage.upload_file(
                    storage_path,
                    content,
                    user_id,
                    content_type
                )
                storage_urls[file.filename] = storage_result
                logger.info(f"Uploaded {file.filename} to storage: {storage_result['path']}")
            except Exception as se:
                logger.warning(f"Storage upload failed for {file.filename}: {str(se)}, falling back to database storage")
                # Fallback to old method if storage fails
                upload.metadata[f"file_content_{file.filename}"] = content.hex()
            
            # Check if ZIP
            if file.filename.lower().endswith('.zip'):
                extracted_files = parser.extract_files_from_zip(content)
                
                for filename, file_content in extracted_files:
                    file_info = parser.detect_and_classify_file(filename, file_content)
                    
                    # Use Gemini to enhance file detection
                    if use_gemini and file_info.columns:
                        try:
                            gemini_suggestion = self._gemini_suggest_file_type(filename, file_info.columns)
                            if gemini_suggestion:
                                gemini_file_insights[filename] = gemini_suggestion
                                logger.info(f"Gemini suggestion for {filename}: {gemini_suggestion}")
                        except Exception as ge:
                            logger.warning(f"Gemini file analysis failed: {ge}")
                    
                    all_files.append(file_info)
                    
                    if file_info.needs_mapping:
                        needs_mapping = True
                    
                    # Store extracted file content (in metadata as fallback)
                    upload.metadata[f"file_content_{filename}"] = file_content.hex()
            else:
                file_info = parser.detect_and_classify_file(file.filename, content)
                
                # Use Gemini to enhance file detection
                if use_gemini and file_info.columns:
                    try:
                        gemini_suggestion = self._gemini_suggest_file_type(file.filename, file_info.columns)
                        if gemini_suggestion:
                            gemini_file_insights[file.filename] = gemini_suggestion
                            logger.info(f"Gemini suggestion for {file.filename}: {gemini_suggestion}")
                    except Exception as ge:
                        logger.warning(f"Gemini file analysis failed: {ge}")
                
                all_files.append(file_info)
                
                if file_info.needs_mapping:
                    needs_mapping = True
                
                # Store content in metadata as fallback
                if file.filename not in storage_urls:
                    upload.metadata[f"file_content_{file.filename}"] = content.hex()
        
        upload.files = all_files
        upload.status = UploadStatus.MAPPING if needs_mapping else UploadStatus.UPLOADED
        upload.metadata["gemini_insights"] = gemini_file_insights
        
        # Save to database
        upload_dict = upload.model_dump(mode='json')
        upload_dict['upload_date'] = upload_dict['upload_date'].isoformat() if hasattr(upload_dict['upload_date'], 'isoformat') else upload_dict['upload_date']
        upload_dict['files'] = [f.model_dump(mode='json') for f in upload.files]
        upload_dict['storage_urls'] = storage_urls
        
        await uploads_collection.create(upload_dict, user_id=user_id)
        
        logger.info(f"Upload created: {upload.id}, {len(all_files)} files, needs_mapping={needs_mapping}, user={user_id}")
        
        return UploadCreateResponse(
            upload_id=upload.id,
            files=all_files,
            message=f"Successfully uploaded {len(all_files)} file(s) with Gemini AI analysis",
            needs_mapping=needs_mapping
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

def _gemini_suggest_file_type(filename: str, columns: List[str]) -> Optional[Dict]:
    """Use Gemini to suggest file type based on filename and columns"""
    try:
        import google.generativeai as genai
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
Analyze this Excel/CSV file for GST filing and suggest its type:

Filename: {filename}
Columns: {', '.join(columns[:15])}

Determine the file type from these options:
- B2B Invoices (registered buyers with GSTIN)
- B2C Sales (unregistered buyers, no GSTIN)
- Credit Notes
- Debit Notes
- Export Invoices
- HSN Summary
- Tax Invoices
- Unknown

Also suggest the GSTR-1 table/section this belongs to.

Return JSON:
{{
    "file_type": "...",
    "gstr_section": "...",
    "confidence": "high/medium/low",
    "reason": "..."
}}
"""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean markdown
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        import json
        return json.loads(response_text)
    except Exception as e:
        logger.warning(f"Gemini file type suggestion failed: {e}")
        return None


@api_router.get("/mapping/suggestions/{upload_id}")
async def get_mapping_suggestions(upload_id: str):
    """
    Get auto-mapping suggestions for uploaded files
    """
    try:
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = Upload(**upload_doc)
        parser = EnhancedFileParser()
        
        suggestions = {}
        
        for file_info in upload.files:
            if not file_info.columns:
                continue
            
            # Get auto-mapping suggestions
            mappings = parser.header_matcher.map_headers(file_info.columns)
            suggested_section = parser.header_matcher.suggest_section(file_info.columns)
            
            suggestions[file_info.filename] = {
                "mappings": [m.model_dump() for m in mappings.values()],
                "suggested_section": suggested_section,
                "confidence": file_info.mapping_confidence
            }
        
        return {"upload_id": upload_id, "suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Mapping suggestions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/mapping/apply/{upload_id}")
async def apply_mapping(
    upload_id: str,
    mappings: Dict[str, List[Dict]] = Body(...)
):
    """
    Apply user-confirmed mappings and proceed to processing
    
    Body format:
    {
        "filename1.xlsx": [
            {"file_header": "...", "canonical_field": "...", "confidence": 1.0, "match_type": "exact"},
            ...
        ]
    }
    """
    try:
        # Store mappings in upload metadata
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload_doc["metadata"]["approved_mappings"] = mappings
        upload_doc["status"] = UploadStatus.UPLOADED.value
        
        await uploads_collection.update(upload_id, upload_doc)
        
        return {"message": "Mappings applied successfully", "upload_id": upload_id}
        
    except Exception as e:
        logger.error(f"Apply mapping error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/process/{upload_id}", response_model=ProcessingResult)
async def process_upload(upload_id: str):
    """
    Process uploaded files with canonical normalization
    """
    try:
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = Upload(**upload_doc)
        
        # Update status
        await uploads_collection.update(upload_id, {"status": UploadStatus.PROCESSING.value})
        
        seller_state_code = upload.metadata.get("seller_state_code", "27")
        parser = EnhancedFileParser(seller_state_code=seller_state_code)
        
        all_invoice_lines = []
        errors = []
        
        # Get approved mappings if any
        approved_mappings = upload.metadata.get("approved_mappings", {})
        
        # Process each file
        for file_info in upload.files:
            if not file_info.detected and file_info.filename not in approved_mappings:
                errors.append(f"File {file_info.filename} needs mapping")
                continue
            
            try:
                # Retrieve file content
                content_hex = upload.metadata.get(f"file_content_{file_info.filename}")
                if not content_hex:
                    errors.append(f"Content not found for {file_info.filename}")
                    continue
                
                content = bytes.fromhex(content_hex)
                
                # Get mappings (either auto or user-approved)
                if file_info.filename in approved_mappings:
                    file_mappings = {
                        m["file_header"]: HeaderMapping(**m)
                        for m in approved_mappings[file_info.filename]
                    }
                else:
                    # Use auto-detected mappings
                    headers = parser.read_headers(content, file_info.filename)
                    file_mappings = parser.header_matcher.map_headers(headers)
                
                # Parse with mappings
                invoice_lines = parser.parse_file_with_mapping(
                    content,
                    file_info.filename,
                    upload_id,
                    file_mappings,
                    file_info.file_type
                )
                
                all_invoice_lines.extend(invoice_lines)
                logger.info(f"Parsed {len(invoice_lines)} lines from {file_info.filename}")
                
            except Exception as e:
                error_msg = f"Error parsing {file_info.filename}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Save invoice lines
        user_id = upload_doc.get('user_id', 'default_user')
        if all_invoice_lines:
            invoice_docs = [line.model_dump(mode='json') for line in all_invoice_lines]
            invoice_docs = [safe_json_response(doc) for doc in invoice_docs]
            await invoice_lines_collection.insert_many(invoice_docs, user_id=user_id)
        
        # Detect document ranges for Table 13
        range_detector = InvoiceRangeDetector()
        document_ranges, non_sequential = range_detector.detect_ranges(
            upload_id,
            [line.model_dump() for line in all_invoice_lines]
        )
        
        # Save document ranges (would need a new collection)
        logger.info(f"Detected {len(document_ranges)} document ranges, {len(non_sequential)} non-sequential")
        
        # Update upload status
        status = UploadStatus.COMPLETED if not errors else UploadStatus.FAILED
        await uploads_collection.update(
            upload_id,
            {
                "status": status.value,
                "processing_errors": errors,
                "metadata.document_ranges_count": len(document_ranges),
                "metadata.non_sequential_count": len(non_sequential)
            }
        )
        
        logger.info(f"Processing completed: {upload_id}, {len(all_invoice_lines)} lines")
        
        return ProcessingResult(
            upload_id=upload_id,
            status=status.value,
            invoice_lines_count=len(all_invoice_lines),
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        await uploads_collection.update(
            upload_id,
            {"status": UploadStatus.FAILED.value, "processing_errors": [str(e)]}
        )
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/generate/{upload_id}")
async def generate_gstr1_json(upload_id: str, use_gemini: bool = True):
    """
    Generate complete GSTR-1 JSON with ALL tables using Gemini AI
    Includes: B2B, B2CL, B2CS (Table 7), CDNR, CDNUR, EXP, EXPWOP, AT, ATADJ, HSN (Table 12), DOC_ISS (Table 13), NIL, and more
    """
    try:
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = Upload(**upload_doc)
        
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
        seller_state_code = upload.metadata.get("seller_state_code", "27")
        
        logger.info(f"Generating GSTR-1 with Gemini AI for {len(invoice_lines)} invoice lines")
        
        # Use Gemini to analyze data before generation
        if use_gemini:
            gemini_insights = gemini_service.generate_filing_insights(invoice_lines)
            logger.info(f"Gemini insights: {gemini_insights.get('key_insights', [])}")
        
        # Detect document ranges for Table 13
        range_detector = InvoiceRangeDetector()
        document_ranges, non_sequential = range_detector.detect_ranges(upload_id, invoice_lines)
        
        # Use Gemini to detect missing invoices
        if use_gemini and document_ranges:
            all_invoice_numbers = [line.get("invoice_no_raw", "") for line in invoice_lines if line.get("invoice_no_raw")]
            gemini_missing = gemini_service.detect_missing_invoices(all_invoice_numbers)
            logger.info(f"Gemini detected {len(gemini_missing.get('missing_invoices', []))} potentially missing invoices")
        
        # Generate complete GSTR-1 with ALL tables using new generator
        complete_generator = CompleteGSTR1Generator(
            gstin=gstin,
            filing_period=filing_period,
            seller_state_code=seller_state_code
        )
        
        gstr1_complete = complete_generator.generate_complete_gstr1(
            invoice_lines, 
            document_ranges,
            use_gemini=use_gemini
        )
        
        # Save to database
        user_id = upload_doc.get('user_id', 'default_user')
        export_dict = {
            "id": str(uuid.uuid4()),
            "upload_id": upload_id,
            "gstin": gstin,
            "fp": filing_period,
            "gstr1_data": gstr1_complete,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "gemini_insights": gemini_insights if use_gemini else {},
            "sections_count": len([k for k, v in gstr1_complete.items() if v and k not in ["gstin", "fp", "gt", "cur_gt", "_validation"]])
        }
        
        export_dict = safe_json_response(export_dict)
        await gstr_exports_collection.insert(export_dict, user_id=user_id)
        
        logger.info(f"Generated complete GSTR-1 for upload {upload_id} with {export_dict['sections_count']} sections")
        
        return safe_json_response({
            "upload_id": upload_id,
            "gstr1": gstr1_complete,
            "sections_generated": [k for k, v in gstr1_complete.items() if v and k not in ["gstin", "fp", "gt", "cur_gt", "_validation"]],
            "validation": gstr1_complete.get("_validation", {}),
            "gemini_insights": gemini_insights if use_gemini else {},
            "document_ranges_count": len(document_ranges),
            "non_sequential_count": len(non_sequential)
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Generation error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/download/{upload_id}/gstr1")
async def download_gstr1_file(upload_id: str):
    """
    Download GSTR-1 JSON file
    """
    try:
        exports = await gstr_exports_collection.find_by_upload(upload_id)
        
        if not exports:
            raise HTTPException(status_code=404, detail="No exports found")
        
        # Get the GSTR-1 export (there should only be one now)
        export_data = exports[0] if exports else None
        
        if not export_data:
            raise HTTPException(status_code=404, detail="GSTR-1 not found")
        
        # Get filing period for filename
        upload_doc = await uploads_collection.find_one(upload_id)
        filing_period = upload_doc.get('metadata', {}).get('filing_period', '012025') if upload_doc else '012025'
        
        # Create JSON string
        json_string = json.dumps(export_data, indent=2)
        
        # Create filename
        filename = f"GSTR1_{filing_period}.json"
        
        # Convert to bytes
        json_bytes = json_string.encode('utf-8')
        
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
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/uploads")
async def list_uploads():
    """List all uploads"""
    try:
        uploads = await uploads_collection.find_all()
        
        # Clean up file content
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
    """Get upload details"""
    try:
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Clean up file content
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
        upload_doc["exports_count"] = len(exports)
        
        return safe_json_response(upload_doc)
        
    except Exception as e:
        logger.error(f"Get upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/preview/{upload_id}")
async def get_preview_data(upload_id: str):
    """Get preview data with breakdowns"""
    try:
        upload_doc = await uploads_collection.find_one(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        invoice_lines = await invoice_lines_collection.find_by_upload(upload_id)
        
        if not invoice_lines:
            return safe_json_response({
                "upload_id": upload_id,
                "summary": {},
                "breakdown": {}
            })
        
        # Calculate summary
        from decimal_utils import parse_money
        
        total_taxable = sum(parse_money(line.get("taxable_value", 0)) for line in invoice_lines)
        total_cgst = sum(parse_money(line.get("computed_tax", {}).get("cgst_amount", 0)) for line in invoice_lines)
        total_sgst = sum(parse_money(line.get("computed_tax", {}).get("sgst_amount", 0)) for line in invoice_lines)
        total_igst = sum(parse_money(line.get("computed_tax", {}).get("igst_amount", 0)) for line in invoice_lines)
        
        # Group by section
        section_counts = {}
        for line in invoice_lines:
            section = line.get("gstr_section", "unknown")
            section_counts[section] = section_counts.get(section, 0) + 1
        
        return safe_json_response({
            "upload_id": upload_id,
            "summary": {
                "total_lines": len(invoice_lines),
                "total_taxable_value": float(total_taxable),
                "total_cgst": float(total_cgst),
                "total_sgst": float(total_sgst),
                "total_igst": float(total_igst),
                "total_tax": float(total_cgst + total_sgst + total_igst)
            },
            "section_breakdown": section_counts
        })
        
    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Include routers
app.include_router(api_router)
app.include_router(auth_routes.router, prefix="/api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("GST Filing Automation API - Schema-Driven GSTR-1 - Starting up")
    logger.info("Features: Decimal Precision, Auto-Mapping, All GSTR-1 Sections")
