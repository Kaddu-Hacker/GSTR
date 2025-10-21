"""
Enhanced GSTR Generator with Portal Compliance
Implements all required fixes for GST portal acceptance
"""

from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
import re
import hashlib
import json


class PortalCompliantGSTRGenerator:
    """
    Generate GST portal-compliant GSTR-1B and GSTR-3B JSON files
    
    Key features:
    - Exact portal field names and structure
    - All required arrays (even if empty)
    - Proper numeric formatting (2 decimals)
    - Robust cancelled invoice detection
    - Document type vocabulary mapping
    - Header metadata (version, hash)
    """
    
    # Portal-standard document type vocabulary
    DOC_TYPE_MAPPING = {
        "invoice": "Invoices for outward supply",
        "tax_invoice": "Invoices for outward supply",
        "credit_note": "Credit Notes",
        "credit": "Credit Notes",
        "debit_note": "Debit Notes",
        "debit": "Debit Notes",
        "delivery_challan": "Delivery Challans",
        "challan": "Delivery Challans",
        "refund_voucher": "Refund Voucher",
        "receipt_voucher": "Receipt Voucher"
    }
    
    def __init__(self, gstin: str, filing_period: str, eco_gstin: str = "07AARCM9332R1CQ", 
                 schema_version: str = "GST3.1.6"):
        """
        Args:
            gstin: Seller's GSTIN (15 characters)
            filing_period: Filing period in MMYYYY format
            eco_gstin: E-commerce operator GSTIN
            schema_version: GST schema version
        """
        self.gstin = gstin
        self.fp = filing_period
        self.eco_gstin = eco_gstin
        self.version = schema_version
    
    def _round_decimal(self, value: Any, decimals: int = 2) -> float:
        """Round value to specified decimals using Decimal for precision"""
        if value is None:
            return 0.0
        decimal_val = Decimal(str(value))
        quantizer = Decimal(f"0.{'0' * decimals}")
        return float(decimal_val.quantize(quantizer, rounding=ROUND_HALF_UP))
    
    def _normalize_doc_type(self, raw_type: str) -> str:
        """Map document type to portal standard vocabulary"""
        if not raw_type:
            return "Invoices for outward supply"
        
        normalized = raw_type.lower().strip()
        
        # Try direct mapping
        if normalized in self.DOC_TYPE_MAPPING:
            return self.DOC_TYPE_MAPPING[normalized]
        
        # Try fuzzy match
        for key, standard_name in self.DOC_TYPE_MAPPING.items():
            if key in normalized:
                return standard_name
        
        # Default
        return "Invoices for outward supply"
    
    def _extract_invoice_components(self, invoice_no: str) -> Tuple[Optional[str], Optional[int], int]:
        """
        Extract prefix, numeric serial, and padding length from invoice number
        
        Returns: (prefix, serial_number, pad_length)
        Example: "QPM1G2612" -> ("QPM1G", 2612, 4)
        """
        if not invoice_no:
            return None, None, 0
        
        # Sanitize: trim, uppercase, remove spaces
        s = str(invoice_no).strip().upper().replace(" ", "")
        
        # Try to match prefix + numeric suffix
        match = re.match(r'^(.+?)(\d{1,12})$', s)
        if match:
            prefix = match.group(1)
            numeric_part = match.group(2)
            serial = int(numeric_part)
            pad_length = len(numeric_part)
            return prefix, serial, pad_length
        
        # Cannot extract numeric serial
        return s, None, 0
    
    def _detect_cancelled_invoices(self, invoice_numbers: List[str], doc_type: str) -> List[Dict]:
        """
        Robust cancelled invoice detection algorithm
        
        Groups by prefix, detects missing serials, computes ranges
        Returns list of document range entries with cancelled counts
        """
        if not invoice_numbers:
            return []
        
        # Group by prefix
        prefix_groups = defaultdict(list)
        non_sequential = []
        
        for inv_no in invoice_numbers:
            prefix, serial, pad_length = self._extract_invoice_components(inv_no)
            
            if prefix and serial is not None:
                prefix_groups[prefix].append({
                    'serial': serial,
                    'pad_length': pad_length,
                    'original': inv_no
                })
            else:
                # Non-sequential invoice (no numeric part)
                non_sequential.append(inv_no)
        
        # Analyze each prefix group
        results = []
        
        for prefix, items in prefix_groups.items():
            # Sort by serial number
            items_sorted = sorted(items, key=lambda x: x['serial'])
            
            # Get unique serials (in case of duplicates)
            serials = sorted(set(item['serial'] for item in items_sorted))
            
            if not serials:
                continue
            
            first_serial = serials[0]
            last_serial = serials[-1]
            found_count = len(serials)
            expected_count = last_serial - first_serial + 1
            missing_count = expected_count - found_count
            
            # Use pad length from first item
            pad_length = items_sorted[0]['pad_length']
            
            # Format with leading zeros
            doc_from = f"{prefix}{str(first_serial).zfill(pad_length)}"
            doc_to = f"{prefix}{str(last_serial).zfill(pad_length)}"
            
            results.append({
                'doc_type': doc_type,
                'doc_from': doc_from,
                'doc_to': doc_to,
                'doc_num': found_count,  # Portal expects count of found documents
                'cancelled': max(0, missing_count)  # Integer count of missing/cancelled
            })
        
        # Handle non-sequential items
        if non_sequential:
            # Report as separate entries
            for inv_no in non_sequential:
                results.append({
                    'doc_type': doc_type,
                    'doc_from': inv_no,
                    'doc_to': inv_no,
                    'doc_num': 1,
                    'cancelled': 0
                })
        
        return results
    
    def generate_b2cs(self, invoice_lines: List[Dict]) -> List[Dict]:
        """
        Generate B2CS table (was Table 7) - B2C supplies to unregistered persons
        Portal-compliant field names and formats
        """
        # Filter sales lines
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("state_code")
            and line.get("gst_rate") is not None
        ]
        
        if not sales_lines:
            return []
        
        # Group by (state_code, gst_rate)
        groups = defaultdict(lambda: {
            'txval': Decimal('0'),
            'iamt': Decimal('0'),
            'camt': Decimal('0'),
            'samt': Decimal('0')
        })
        
        for line in sales_lines:
            state_code = str(line['state_code']).zfill(2)  # Ensure 2 digits with leading zero
            gst_rate = line['gst_rate']
            key = (state_code, gst_rate)
            
            groups[key]['txval'] += Decimal(str(line.get('taxable_value', 0)))
            groups[key]['iamt'] += Decimal(str(line.get('igst_amount', 0)))
            groups[key]['camt'] += Decimal(str(line.get('cgst_amount', 0)))
            groups[key]['samt'] += Decimal(str(line.get('sgst_amount', 0)))
        
        # Build B2CS entries with portal field names
        b2cs_entries = []
        for (state_code, gst_rate), amounts in groups.items():
            entry = {
                'pos': state_code,  # Place of supply - string with leading zero
                'rate': self._round_decimal(gst_rate, 2),  # GST rate - numeric
                'txval': self._round_decimal(amounts['txval'], 2),  # Taxable value
                'iamt': self._round_decimal(amounts['iamt'], 2),  # IGST
                'camt': self._round_decimal(amounts['camt'], 2),  # CGST
                'samt': self._round_decimal(amounts['samt'], 2)   # SGST
            }
            b2cs_entries.append(entry)
        
        # Sort by state code and rate
        b2cs_entries.sort(key=lambda x: (x['pos'], x['rate']))
        
        return b2cs_entries
    
    def generate_doc_iss(self, invoice_lines: List[Dict]) -> List[Dict]:
        """
        Generate DOC_ISS table (was Table 13) - Documents Issued
        Uses robust cancelled detection algorithm
        """
        # Filter tax invoice entries
        invoice_entries = [
            line for line in invoice_lines
            if line.get("file_type") == "tax_invoice"
            and line.get("invoice_no")
        ]
        
        if not invoice_entries:
            return []
        
        # Group by document type
        type_groups = defaultdict(list)
        for line in invoice_entries:
            raw_type = line.get("invoice_type", "Invoice")
            doc_type = self._normalize_doc_type(raw_type)
            type_groups[doc_type].append(line["invoice_no"])
        
        # Detect ranges and cancelled for each type
        all_ranges = []
        for doc_type, invoice_numbers in type_groups.items():
            ranges = self._detect_cancelled_invoices(invoice_numbers, doc_type)
            all_ranges.extend(ranges)
        
        # Sort by document type priority
        doc_type_order = {
            "Invoices for outward supply": 1,
            "Credit Notes": 2,
            "Debit Notes": 3,
            "Delivery Challans": 4,
            "Refund Voucher": 5,
            "Receipt Voucher": 6
        }
        all_ranges.sort(key=lambda x: (doc_type_order.get(x['doc_type'], 99), x['doc_from']))
        
        return all_ranges
    
    def generate_eco_supplies(self, invoice_lines: List[Dict]) -> Dict[str, Any]:
        """
        Generate ECO supplies section (was Table 14)
        Returns nested structure with eco_tcs (14a) and eco_9_5 (14b)
        """
        # Filter sales lines
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("taxable_value") is not None
        ]
        
        if not sales_lines:
            return {'eco_tcs': [], 'eco_9_5': []}
        
        # Aggregate totals (all go to 14a for Meesho - ECO collects TCS)
        totals = {
            'txval': Decimal('0'),
            'iamt': Decimal('0'),
            'camt': Decimal('0'),
            'samt': Decimal('0')
        }
        
        for line in sales_lines:
            totals['txval'] += Decimal(str(line.get('taxable_value', 0)))
            totals['iamt'] += Decimal(str(line.get('igst_amount', 0)))
            totals['camt'] += Decimal(str(line.get('cgst_amount', 0)))
            totals['samt'] += Decimal(str(line.get('sgst_amount', 0)))
        
        # Build ECO entry
        eco_entry = {
            'eco_gstin': self.eco_gstin,
            'txval': self._round_decimal(totals['txval'], 2),
            'camt': self._round_decimal(totals['camt'], 2),
            'samt': self._round_decimal(totals['samt'], 2),
            'iamt': self._round_decimal(totals['iamt'], 2)
        }
        
        # Return nested structure (14a and 14b)
        # For Meesho, all supplies are 14(a) - ECO collects TCS
        # 14(b) is for supplies where ECO is liable to pay tax u/s 9(5) - rare for goods
        return {
            'eco_tcs': [eco_entry],  # Table 14(a)
            'eco_9_5': []  # Table 14(b) - empty for typical Meesho scenario
        }
    
    def generate_gstr1b(self, invoice_lines: List[Dict]) -> Dict[str, Any]:
        """
        Generate complete portal-compliant GSTR-1B JSON
        
        Includes:
        - Proper headers (gstin, fp, version, hash)
        - All required arrays (even if empty)
        - Correct field names matching portal schema
        """
        # Generate each section
        b2cs = self.generate_b2cs(invoice_lines)
        doc_iss = self.generate_doc_iss(invoice_lines)
        eco_supplies = self.generate_eco_supplies(invoice_lines)
        
        # Build complete GSTR-1B with all required fields
        gstr1b = {
            # Header metadata
            'gstin': self.gstin,
            'fp': self.fp,
            'version': self.version,
            'hash': '',  # Portal may compute or ignore, but field expected
            
            # All required arrays (portal expects these keys)
            'b2b': [],  # B2B supplies - empty for B2C-only sellers
            'b2cl': [],  # B2C Large (>2.5L) - empty if none
            'b2cs': b2cs,  # B2C Small - our main table
            'cdnr': [],  # Credit/Debit notes registered - empty if none
            'cdnur': [],  # Credit/Debit notes unregistered - empty if none
            'exp': [],  # Exports - empty if none
            'at': [],  # Tax liability (Advance received) - empty if none
            'atadj': [],  # Advance adjusted - empty if none
            'exemp': [],  # Nil rated, exempted - empty if none
            'hsn': [],  # HSN summary - can be empty
            'doc_iss': doc_iss,  # Documents issued
            'eco_supplies': eco_supplies,  # ECO supplies nested structure
            'nil_supplies': {}  # Nil supplies - can be empty object
        }
        
        return gstr1b
    
    def generate_gstr3b(self, invoice_lines: List[Dict]) -> Dict[str, Any]:
        """
        Generate complete portal-compliant GSTR-3B JSON
        
        Key sections:
        - 3.1(a): Outward taxable supplies (non-ECO)
        - 3.1.1(ii): Supplies through ECO
        - 3.2: Inter-state to unregistered
        """
        # Filter sales lines
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("taxable_value") is not None
        ]
        
        # Initialize aggregates
        eco_totals = {'txval': Decimal('0'), 'iamt': Decimal('0'), 'camt': Decimal('0'), 'samt': Decimal('0')}
        interstate_totals = {'txval': Decimal('0'), 'iamt': Decimal('0')}
        
        for line in sales_lines:
            txval = Decimal(str(line.get('taxable_value', 0)))
            iamt = Decimal(str(line.get('igst_amount', 0)))
            camt = Decimal(str(line.get('cgst_amount', 0)))
            samt = Decimal(str(line.get('sgst_amount', 0)))
            
            # All go to ECO section (3.1.1(ii))
            eco_totals['txval'] += txval
            eco_totals['iamt'] += iamt
            eco_totals['camt'] += camt
            eco_totals['samt'] += samt
            
            # If inter-state (IGST > 0), also add to Section 3.2
            if line.get('is_intra_state') == False:
                interstate_totals['txval'] += txval
                interstate_totals['iamt'] += iamt
        
        # Build GSTR-3B structure
        gstr3b = {
            'gstin': self.gstin,
            'fp': self.fp,
            'version': self.version,
            'hash': '',
            
            # Section 3.1(a) - Outward taxable supplies (non-ECO)
            # Empty for pure ECO sellers
            'sec_31a': {
                'txval': 0.0,
                'iamt': 0.0,
                'camt': 0.0,
                'samt': 0.0,
                'csamt': 0.0
            },
            
            # Section 3.1.1(ii) - Supplies through ECO
            'sec_311_ii': {
                'txval': self._round_decimal(eco_totals['txval'], 2),
                'iamt': self._round_decimal(eco_totals['iamt'], 2),
                'camt': self._round_decimal(eco_totals['camt'], 2),
                'samt': self._round_decimal(eco_totals['samt'], 2),
                'csamt': 0.0
            },
            
            # Section 3.2 - Inter-state supplies to unregistered
            'sec_32': {
                'txval': self._round_decimal(interstate_totals['txval'], 2),
                'iamt': self._round_decimal(interstate_totals['iamt'], 2)
            }
        }
        
        return gstr3b
    
    def validate_output(self, gstr1b: Dict, gstr3b: Dict) -> List[str]:
        """
        Validate portal compliance and reconcile GSTR-1B with GSTR-3B
        Returns list of validation warnings
        """
        warnings = []
        
        # Check required keys present
        required_gstr1b_keys = ['gstin', 'fp', 'version', 'b2cs', 'doc_iss', 'eco_supplies']
        for key in required_gstr1b_keys:
            if key not in gstr1b:
                warnings.append(f"Missing required key in GSTR-1B: {key}")
        
        required_gstr3b_keys = ['gstin', 'fp', 'version', 'sec_31a', 'sec_311_ii', 'sec_32']
        for key in required_gstr3b_keys:
            if key not in gstr3b:
                warnings.append(f"Missing required key in GSTR-3B: {key}")
        
        # Validate numeric precision (all amounts should be 2 decimals)
        def check_decimals(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    check_decimals(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_decimals(item, f"{path}[{i}]")
            elif isinstance(obj, float):
                # Check if more than 2 decimal places
                decimal_str = f"{obj:.10f}".rstrip('0')
                if '.' in decimal_str and len(decimal_str.split('.')[1]) > 2:
                    warnings.append(f"Value at {path} has more than 2 decimals: {obj}")
        
        check_decimals(gstr1b, "GSTR1B")
        check_decimals(gstr3b, "GSTR3B")
        
        # Reconcile ECO supplies between GSTR-1B and GSTR-3B
        eco_1b_txval = sum(item['txval'] for item in gstr1b.get('eco_supplies', {}).get('eco_tcs', []))
        eco_3b_txval = gstr3b.get('sec_311_ii', {}).get('txval', 0)
        
        if abs(eco_1b_txval - eco_3b_txval) > 0.02:
            warnings.append(
                f"ECO supplies mismatch: GSTR-1B ECO = ₹{eco_1b_txval:.2f}, "
                f"GSTR-3B Section 3.1.1(ii) = ₹{eco_3b_txval:.2f}"
            )
        
        # Validate B2CS matches ECO supplies (they should be equal for pure ECO sellers)
        b2cs_txval = sum(item['txval'] for item in gstr1b.get('b2cs', []))
        if abs(b2cs_txval - eco_1b_txval) > 0.02:
            warnings.append(
                f"B2CS (₹{b2cs_txval:.2f}) and ECO supplies (₹{eco_1b_txval:.2f}) should match"
            )
        
        return warnings
    
    def compute_hash(self, json_data: Dict) -> str:
        """
        Compute SHA-256 hash of JSON data (if portal requires it)
        """
        json_str = json.dumps(json_data, sort_keys=True, separators=(',', ':'))
        hash_obj = hashlib.sha256(json_str.encode('utf-8'))
        return hash_obj.hexdigest()
