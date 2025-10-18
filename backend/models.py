from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class FileType(str, Enum):
    TCS_SALES = "tcs_sales"
    TCS_SALES_RETURN = "tcs_sales_return"
    TAX_INVOICE = "tax_invoice"
    UNKNOWN = "unknown"


class UploadStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileInfo(BaseModel):
    filename: str
    file_type: FileType
    detected: bool = False
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None


class Upload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"  # Can be extended for multi-user support
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    status: UploadStatus = UploadStatus.UPLOADED
    files: List[FileInfo] = []
    processing_errors: List[str] = []
    metadata: Dict[str, Any] = {}


class InvoiceLine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    upload_id: str
    file_type: FileType
    
    # Original Meesho columns
    gst_rate: Optional[float] = None
    total_taxable_sale_value: Optional[float] = None
    end_customer_state_new: Optional[str] = None
    invoice_type: Optional[str] = None
    invoice_no: Optional[str] = None
    
    # Computed fields
    state_code: Optional[str] = None
    is_return: bool = False
    taxable_value: Optional[float] = None  # After applying return negative
    tax_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    is_intra_state: Optional[bool] = None
    
    # Additional fields from tax invoice
    invoice_date: Optional[str] = None
    invoice_serial: Optional[str] = None
    
    # Raw data for reference
    raw_data: Dict[str, Any] = {}


class Table7Entry(BaseModel):
    """B2C Others - Table 7 for GSTR-1B"""
    pos: str  # Place of supply (state code)
    rate: float  # GST rate
    txval: float  # Taxable value
    iamt: float = 0.0  # IGST amount
    camt: float = 0.0  # CGST amount
    samt: float = 0.0  # SGST amount


class Table13Entry(BaseModel):
    """Documents Issued - Table 13 for GSTR-1B"""
    doc_type: str  # Document type (e.g., "Invoices for outward supply")
    doc_num: int  # Number of documents issued
    doc_from: str  # Serial number from
    doc_to: str  # Serial number to
    total_count: int  # Total count
    cancelled: int = 0  # Cancelled documents


class Table14Entry(BaseModel):
    """Supplies through ECO - Table 14 for GSTR-1B"""
    eco_gstin: str  # GSTIN of ECO (Meesho)
    txval: float  # Taxable value
    iamt: float = 0.0  # IGST amount
    camt: float = 0.0  # CGST amount
    samt: float = 0.0  # SGST amount


class GSTR1BOutput(BaseModel):
    """Complete GSTR-1B JSON structure"""
    gstin: str
    fp: str  # Filing period (MMYYYY)
    table7: List[Table7Entry] = []
    table13: List[Table13Entry] = []
    table14: List[Table14Entry] = []


class GSTR3BSection31(BaseModel):
    """GSTR-3B Section 3.1 - Outward taxable supplies"""
    txval: float  # Taxable value
    iamt: float = 0.0  # IGST amount
    camt: float = 0.0  # CGST amount
    samt: float = 0.0  # SGST amount
    csamt: float = 0.0  # Cess amount


class GSTR3BOutput(BaseModel):
    """GSTR-3B JSON structure (simplified)"""
    gstin: str
    fp: str  # Filing period (MMYYYY)
    section_31: GSTR3BSection31  # Outward taxable supplies


class GSTRExport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    upload_id: str
    export_type: str  # "GSTR1B" or "GSTR3B"
    export_date: datetime = Field(default_factory=datetime.utcnow)
    json_data: Dict[str, Any]
    validation_warnings: List[str] = []


class ProcessingResult(BaseModel):
    """Result of processing uploaded files"""
    upload_id: str
    status: str
    invoice_lines_count: int
    validation_warnings: List[str] = []
    errors: List[str] = []


class UploadCreateResponse(BaseModel):
    upload_id: str
    files: List[FileInfo]
    message: str
