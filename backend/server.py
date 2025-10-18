from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

# Import our custom modules
from models import (
    Upload, UploadStatus, FileType, FileInfo,
    InvoiceLine, GSTRExport, ProcessingResult,
    UploadCreateResponse, GSTR1BOutput, GSTR3BOutput
)
from parser import FileParser
from gstr_generator import GSTRGenerator

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Collections
uploads_collection = db.uploads
invoice_lines_collection = db.invoice_lines
gstr_exports_collection = db.gstr_exports

# Create the main app without a prefix
app = FastAPI(title="GST Filing Automation API")

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
    return {"message": "GST Filing Automation API", "version": "1.0"}


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
            # In production, use file storage (S3, etc.)
            upload.metadata[f"file_content_{f['filename']}"] = f.get("content", b"").hex()
        
        upload.files = file_infos
        
        # Save to MongoDB
        upload_dict = upload.model_dump()
        upload_dict['upload_date'] = upload_dict['upload_date'].isoformat()
        
        await uploads_collection.insert_one(upload_dict)
        
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
    """
    try:
        # Get upload record
        upload_doc = await uploads_collection.find_one({"id": upload_id}, {"_id": 0})
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = Upload(**upload_doc)
        
        # Update status
        await uploads_collection.update_one(
            {"id": upload_id},
            {"$set": {"status": UploadStatus.PROCESSING.value}}
        )
        
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
                # Retrieve file content from metadata (temporary storage)
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
        
        # Save invoice lines to MongoDB
        if all_invoice_lines:
            invoice_docs = [line.model_dump() for line in all_invoice_lines]
            await invoice_lines_collection.insert_many(invoice_docs)
        
        # Update upload status
        status = UploadStatus.COMPLETED if not errors else UploadStatus.FAILED
        await uploads_collection.update_one(
            {"id": upload_id},
            {
                "$set": {
                    "status": status.value,
                    "processing_errors": errors
                }
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
        await uploads_collection.update_one(
            {"id": upload_id},
            {
                "$set": {
                    "status": UploadStatus.FAILED.value,
                    "processing_errors": [str(e)]
                }
            }
        )
        
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/generate/{upload_id}")
async def generate_gstr_json(upload_id: str):
    """
    Generate GSTR-1B and GSTR-3B JSON files
    """
    try:
        # Get upload record
        upload_doc = await uploads_collection.find_one({"id": upload_id}, {"_id": 0})
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
        invoice_lines_cursor = invoice_lines_collection.find(
            {"upload_id": upload_id},
            {"_id": 0}
        )
        invoice_lines = await invoice_lines_cursor.to_list(length=None)
        
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
        
        # Save to MongoDB
        gstr1b_export = GSTRExport(
            upload_id=upload_id,
            export_type="GSTR1B",
            json_data=gstr1b.model_dump(),
            validation_warnings=warnings
        )
        
        gstr3b_export = GSTRExport(
            upload_id=upload_id,
            export_type="GSTR3B",
            json_data=gstr3b.model_dump(),
            validation_warnings=warnings
        )
        
        # Save exports
        await gstr_exports_collection.insert_one(gstr1b_export.model_dump())
        await gstr_exports_collection.insert_one(gstr3b_export.model_dump())
        
        logger.info(f"Generated GSTR JSON files for upload {upload_id}")
        
        return {
            "upload_id": upload_id,
            "gstr1b": gstr1b.model_dump(),
            "gstr3b": gstr3b.model_dump(),
            "validation_warnings": warnings
        }
        
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/downloads/{upload_id}")
async def get_downloads(upload_id: str):
    """
    Get available downloads for an upload
    """
    try:
        # Get exports
        exports_cursor = gstr_exports_collection.find(
            {"upload_id": upload_id},
            {"_id": 0}
        )
        exports = await exports_cursor.to_list(length=None)
        
        if not exports:
            raise HTTPException(status_code=404, detail="No exports found for this upload")
        
        return {
            "upload_id": upload_id,
            "exports": exports
        }
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/uploads")
async def list_uploads():
    """
    List all uploads
    """
    try:
        uploads_cursor = uploads_collection.find({}, {"_id": 0}).sort("upload_date", -1)
        uploads = await uploads_cursor.to_list(length=100)
        
        # Clean up file content from metadata for listing
        for upload in uploads:
            if "metadata" in upload:
                upload["metadata"] = {
                    k: v for k, v in upload["metadata"].items()
                    if not k.startswith("file_content_")
                }
        
        return {"uploads": uploads}
        
    except Exception as e:
        logger.error(f"List uploads error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/upload/{upload_id}")
async def get_upload_details(upload_id: str):
    """
    Get upload details with processing status
    """
    try:
        upload_doc = await uploads_collection.find_one({"id": upload_id}, {"_id": 0})
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Clean up file content from metadata
        if "metadata" in upload_doc:
            upload_doc["metadata"] = {
                k: v for k, v in upload_doc["metadata"].items()
                if not k.startswith("file_content_")
            }
        
        # Get invoice lines count
        invoice_count = await invoice_lines_collection.count_documents({"upload_id": upload_id})
        upload_doc["invoice_lines_count"] = invoice_count
        
        # Get exports
        exports_cursor = gstr_exports_collection.find({"upload_id": upload_id}, {"_id": 0, "json_data": 0})
        exports = await exports_cursor.to_list(length=None)
        upload_doc["exports"] = exports
        
        return upload_doc
        
    except Exception as e:
        logger.error(f"Get upload details error: {str(e)}")
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()