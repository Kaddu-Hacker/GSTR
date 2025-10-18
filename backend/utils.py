import re
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from models import FileType


# State name to state code mapping
STATE_CODE_MAPPING = {
    "andhra pradesh": "37",
    "arunachal pradesh": "12",
    "assam": "18",
    "bihar": "10",
    "chhattisgarh": "22",
    "goa": "30",
    "gujarat": "24",
    "haryana": "06",
    "himachal pradesh": "02",
    "jharkhand": "20",
    "karnataka": "29",
    "kerala": "32",
    "madhya pradesh": "23",
    "maharashtra": "27",
    "manipur": "14",
    "meghalaya": "17",
    "mizoram": "15",
    "nagaland": "13",
    "odisha": "21",
    "punjab": "03",
    "rajasthan": "08",
    "sikkim": "11",
    "tamil nadu": "33",
    "telangana": "36",
    "tripura": "16",
    "uttar pradesh": "09",
    "uttarakhand": "05",
    "west bengal": "19",
    "andaman and nicobar islands": "35",
    "chandigarh": "04",
    "dadra and nagar haveli and daman and diu": "26",
    "delhi": "07",
    "jammu and kashmir": "01",
    "ladakh": "38",
    "lakshadweep": "31",
    "puducherry": "34",
}


def normalize_state_to_code(state_name: str) -> Optional[str]:
    """Convert state name to state code"""
    if not state_name:
        return None
    
    # Clean and normalize
    normalized = state_name.strip().lower()
    
    # Direct lookup
    if normalized in STATE_CODE_MAPPING:
        return STATE_CODE_MAPPING[normalized]
    
    # Try partial match
    for state, code in STATE_CODE_MAPPING.items():
        if state in normalized or normalized in state:
            return code
    
    return None


def detect_file_type(filename: str, columns: List[str]) -> FileType:
    """Auto-detect file type based on filename and columns"""
    filename_lower = filename.lower()
    
    # Check by filename patterns
    if "tcs_sales_return" in filename_lower or "sales_return" in filename_lower:
        return FileType.TCS_SALES_RETURN
    elif "tcs_sales" in filename_lower:
        return FileType.TCS_SALES
    elif "tax_invoice" in filename_lower or "invoice_details" in filename_lower:
        return FileType.TAX_INVOICE
    
    # Check by column headers
    columns_lower = [col.lower() for col in columns]
    
    # Tax invoice typically has "Type" and "Invoice No." columns
    if any("type" in col for col in columns_lower) and any("invoice" in col and "no" in col for col in columns_lower):
        return FileType.TAX_INVOICE
    
    # TCS sales and returns have gst_rate and total_taxable_sale_value
    if "gst_rate" in columns_lower and "total_taxable_sale_value" in columns_lower:
        if "return" in filename_lower:
            return FileType.TCS_SALES_RETURN
        return FileType.TCS_SALES
    
    return FileType.UNKNOWN


def compute_tax_split(taxable_value: float, gst_rate: float, seller_state: str, customer_state: str) -> Dict[str, float]:
    """
    Compute CGST/SGST/IGST split based on intra-state or inter-state transaction
    Uses Decimal for precise calculations
    """
    taxable = Decimal(str(taxable_value))
    rate = Decimal(str(gst_rate))
    
    # Calculate total tax
    tax_amount = (taxable * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Determine if intra-state or inter-state
    is_intra_state = seller_state == customer_state
    
    if is_intra_state:
        # Split equally between CGST and SGST
        cgst = (tax_amount / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = tax_amount - cgst  # Remaining to avoid rounding issues
        igst = Decimal("0")
    else:
        # All goes to IGST
        igst = tax_amount
        cgst = Decimal("0")
        sgst = Decimal("0")
    
    return {
        "tax_amount": float(tax_amount),
        "cgst_amount": float(cgst),
        "sgst_amount": float(sgst),
        "igst_amount": float(igst),
        "is_intra_state": is_intra_state
    }


def extract_invoice_serial(invoice_no: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract prefix and numeric serial from invoice number
    Returns (prefix, serial_number)
    Example: "INV-2024-001" -> ("INV-2024-", 1)
    """
    if not invoice_no:
        return None, None
    
    # Sanitize
    sanitized = str(invoice_no).strip()
    
    # Try to match prefix + numeric suffix pattern
    match = re.match(r'^(.*?)(\d{1,10})$', sanitized)
    if match:
        prefix = match.group(1)
        serial = int(match.group(2))
        return prefix, serial
    
    return sanitized, None


def detect_invoice_ranges(invoice_numbers: List[str]) -> List[Dict]:
    """
    Detect invoice serial ranges and missing numbers
    Groups by prefix and finds first, last, and missing serials
    """
    if not invoice_numbers:
        return []
    
    # Group by prefix
    prefix_groups: Dict[str, List[int]] = {}
    
    for inv_no in invoice_numbers:
        prefix, serial = extract_invoice_serial(inv_no)
        if prefix and serial is not None:
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(serial)
    
    # Analyze each group
    ranges = []
    for prefix, serials in prefix_groups.items():
        serials_sorted = sorted(set(serials))
        if not serials_sorted:
            continue
        
        first = serials_sorted[0]
        last = serials_sorted[-1]
        found_count = len(serials_sorted)
        expected_count = last - first + 1
        
        # Find missing numbers
        missing = []
        for i in range(first, last + 1):
            if i not in serials_sorted:
                missing.append(i)
        
        ranges.append({
            "prefix": prefix,
            "doc_from": f"{prefix}{first}",
            "doc_to": f"{prefix}{last}",
            "first_serial": first,
            "last_serial": last,
            "found_count": found_count,
            "expected_count": expected_count,
            "missing_count": len(missing),
            "missing_numbers": missing[:10]  # Limit to first 10 for display
        })
    
    return ranges


def clean_numeric_value(value) -> Optional[float]:
    """Clean and convert numeric value, handling various formats"""
    if value is None or value == "":
        return None
    
    try:
        # If already a number
        if isinstance(value, (int, float)):
            result = float(value)
            # Check for NaN or Infinity
            if not math.isfinite(result):
                return None
            return result
        
        # If string, clean it
        if isinstance(value, str):
            # Remove currency symbols, commas, spaces
            cleaned = value.replace(",", "").replace("₹", "").replace("Rs", "").strip()
            result = float(cleaned)
            # Check for NaN or Infinity
            if not math.isfinite(result):
                return None
            return result
        
        return None
    except (ValueError, TypeError):
        return None


def validate_gst_rate(rate: Optional[float]) -> bool:
    """Validate if GST rate is valid"""
    if rate is None:
        return False
    
    # Valid GST rates in India
    valid_rates = [0, 0.25, 3, 5, 12, 18, 28]
    return rate in valid_rates


def group_by_state_and_rate(invoice_lines: List[Dict]) -> Dict[Tuple[str, float], Dict]:
    """
    Group invoice lines by state_code and gst_rate
    Returns aggregated data for each combination
    """
    groups: Dict[Tuple[str, float], Dict] = {}
    
    for line in invoice_lines:
        state_code = line.get("state_code")
        gst_rate = line.get("gst_rate")
        
        if not state_code or gst_rate is None:
            continue
        
        key = (state_code, gst_rate)
        
        if key not in groups:
            groups[key] = {
                "state_code": state_code,
                "gst_rate": gst_rate,
                "taxable_value": Decimal("0"),
                "cgst_amount": Decimal("0"),
                "sgst_amount": Decimal("0"),
                "igst_amount": Decimal("0"),
                "count": 0
            }
        
        # Aggregate using Decimal for precision
        groups[key]["taxable_value"] += Decimal(str(line.get("taxable_value") or 0))
        groups[key]["cgst_amount"] += Decimal(str(line.get("cgst_amount") or 0))
        groups[key]["sgst_amount"] += Decimal(str(line.get("sgst_amount") or 0))
        groups[key]["igst_amount"] += Decimal(str(line.get("igst_amount") or 0))
        groups[key]["count"] += 1
    
    # Convert Decimal back to float with rounding
    for key in groups:
        groups[key]["taxable_value"] = float(groups[key]["taxable_value"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        groups[key]["cgst_amount"] = float(groups[key]["cgst_amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        groups[key]["sgst_amount"] = float(groups[key]["sgst_amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        groups[key]["igst_amount"] = float(groups[key]["igst_amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    
    return groups
