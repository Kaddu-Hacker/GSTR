"""Canonical data models for schema-driven GSTR-1 generation"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
from decimal import Decimal


class FileType(str, Enum):
    TCS_SALES = "tcs_sales"
    TCS_SALES_RETURN = "tcs_sales_return"
    TAX_INVOICE = "tax_invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    HSN_SUMMARY = "hsn_summary"
    B2B_INVOICES = "b2b_invoices"
    UNKNOWN = "unknown"


class UploadStatus(str, Enum):
    UPLOADED = "uploaded"
    MAPPING = "mapping"  # Needs header mapping
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    TAX_INVOICE = "tax_invoice"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    DELIVERY_CHALLAN = "delivery_challan"
    REFUND_VOUCHER = "refund_voucher"
    RECEIPT_VOUCHER = "receipt_voucher"


class GSTRSection(str, Enum):
    B2B = "b2b"
    B2CL = "b2cl"
    B2CS = "b2cs"
    CDNR = "cdnr"
    CDNUR = "cdnur"
    EXP = "exp"
    AT = "at"
    ATADJ = "atadj"
    HSN = "hsn"
    DOC_ISS = "doc_iss"
    ECO_REG = "eco_reg"  # ECO registered supplies (14a)
    ECO_UNREG = "eco_unreg"  # ECO unregistered supplies (14b)


class FileInfo(BaseModel):
    filename: str
    file_type: FileType
    detected: bool = False
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    mapping_confidence: Optional[float] = None  # Auto-mapping confidence (0-1)
    needs_mapping: bool = False


class HeaderMapping(BaseModel):
    """Mapping from file header to canonical field"""
    file_header: str
    canonical_field: str
    confidence: float  # 0-1 score
    match_type: str  # 'exact', 'substring', 'fuzzy'


class MappingTemplate(BaseModel):
    """Saved mapping template for reuse"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Meesho TCS Sales"
    platform: str  # e.g., "meesho"
    file_type: FileType
    mappings: List[HeaderMapping]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Upload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    status: UploadStatus = UploadStatus.UPLOADED
    files: List[FileInfo] = []
    processing_errors: List[str] = []
    metadata: Dict[str, Any] = {}
    mapping_template_id: Optional[str] = None


class CanonicalInvoiceLine(BaseModel):
    """
    Canonical invoice line with normalized fields and Decimal precision
    This is the core data structure after parsing and normalization
    """
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    upload_id: str
    
    # Core identification
    invoice_no_raw: str  # Original invoice number
    invoice_no_norm: str  # Normalized: uppercase, trimmed
    doc_type: DocumentType
    invoice_date: Optional[str] = None  # ISO YYYY-MM-DD
    
    # Buyer information
    gstin_uin: Optional[str] = None  # Buyer GSTIN (15 chars) or UIN
    buyer_name: Optional[str] = None
    
    # Place of supply
    place_of_supply_state: Optional[str] = None  # State name
    place_of_supply_code: str  # 2-digit state code (required)
    
    # Monetary values (stored as Decimal for precision)
    taxable_value_raw: str  # Store as string to preserve precision
    taxable_value: float  # Rounded for display
    gst_rate: float
    
    # Tax computation (computed fields)
    computed_tax: Dict[str, Any] = {}  # {cgst, sgst, igst, tax_amount, rounding_diff}
    
    # Flags
    is_return: bool = False
    is_reverse_charge: bool = False
    is_intra_state: bool = False
    
    # Origin and classification
    origin: str = "manual"  # 'meesho', 'manual', etc.
    gstr_section: Optional[GSTRSection] = None  # Auto-detected section
    file_type: FileType
    
    # HSN details (if available)
    hsn_code: Optional[str] = None
    description: Optional[str] = None
    uqc: Optional[str] = None
    quantity: Optional[float] = None
    
    # Export details (if applicable)
    shipping_bill_no: Optional[str] = None
    shipping_bill_date: Optional[str] = None
    port_code: Optional[str] = None
    
    # Audit
    raw_data: Dict[str, Any] = {}  # Original row data
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentRange(BaseModel):
    """Document serial range for Table 13"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    upload_id: str
    doc_type: DocumentType
    prefix: str
    first_serial: int
    last_serial: int
    found_count: int  # Actual documents found
    expected_count: int  # last - first + 1
    cancelled_count: int
    cancelled_list: List[int] = []  # List of missing serial numbers
    cancelled_ranges: List[Dict[str, int]] = []  # [{start, end}, ...]
    doc_from: str  # Formatted: prefix + first_serial
    doc_to: str  # Formatted: prefix + last_serial
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NonSequentialDoc(BaseModel):
    """Non-sequential documents that need manual verification"""
    upload_id: str
    doc_type: DocumentType
    invoice_numbers: List[str]
    count: int


class GSTR1Schema(BaseModel):
    """Schema definition for GSTR-1 section"""
    form: str = "GSTR-1"
    section: GSTRSection
    version: str  # e.g., "3.1.6"
    fields: List[Dict[str, Any]]  # Field definitions
    required_fields: List[str]
    validation_rules: Dict[str, Any] = {}


class GSTR1Export(BaseModel):
    """Generated GSTR-1 JSON export"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    upload_id: str
    gstin: str
    fp: str  # Filing period MMYYYY
    version: str  # Schema version
    
    # All GSTR-1 sections
    b2b: List[Dict[str, Any]] = []
    b2cl: List[Dict[str, Any]] = []
    b2cs: List[Dict[str, Any]] = []
    cdnr: List[Dict[str, Any]] = []
    cdnur: List[Dict[str, Any]] = []
    exp: List[Dict[str, Any]] = []
    at: List[Dict[str, Any]] = []
    atadj: List[Dict[str, Any]] = []
    hsn: List[Dict[str, Any]] = []
    doc_iss: List[Dict[str, Any]] = []
    
    # Validation
    validation_warnings: List[str] = []
    validation_errors: List[str] = []
    reconciliation_report: Dict[str, Any] = {}
    
    export_date: datetime = Field(default_factory=datetime.utcnow)


class ProcessingResult(BaseModel):
    """Result of processing uploaded files"""
    upload_id: str
    status: str
    invoice_lines_count: int
    validation_warnings: List[str] = []
    errors: List[str] = []
    needs_mapping: bool = False
    mapping_suggestions: List[HeaderMapping] = []


class UploadCreateResponse(BaseModel):
    upload_id: str
    files: List[FileInfo]
    message: str
    needs_mapping: bool = False
