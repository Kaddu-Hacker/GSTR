"""Robust invoice range detection for Table 13 (Document Issued)"""

import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from models_canonical import DocumentRange, DocumentType, NonSequentialDoc


class InvoiceRangeDetector:
    """Detect invoice serial ranges and missing/cancelled documents"""
    
    @staticmethod
    def normalize_invoice_no(invoice_no: str) -> str:
        """Normalize invoice number: trim and uppercase"""
        if not invoice_no:
            return ""
        return str(invoice_no).strip().upper()
    
    @staticmethod
    def split_prefix_number(invoice_no_norm: str) -> Optional[Tuple[str, int, int]]:
        """
        Split normalized invoice number into prefix and numeric suffix
        
        Returns:
            (prefix, number, pad_length) or None if not sequential
        
        Examples:
            "INV001" -> ("INV", 1, 3)
            "AB-2024-0042" -> ("AB-2024-", 42, 4)
            "XYZ123" -> ("XYZ", 123, 3)
        """
        # Match prefix (any chars) followed by numeric suffix (1-12 digits)
        match = re.match(r'^(.+?)(\d{1,12})$', invoice_no_norm)
        
        if match:
            prefix = match.group(1)
            num_str = match.group(2)
            number = int(num_str)
            pad_length = len(num_str)
            return (prefix, number, pad_length)
        
        return None
    
    @staticmethod
    def format_serial(prefix: str, number: int, pad_length: int) -> str:
        """Format serial number with proper padding"""
        return f"{prefix}{str(number).zfill(pad_length)}"
    
    def detect_ranges(
        self,
        upload_id: str,
        invoice_lines: List[Dict]
    ) -> Tuple[List[DocumentRange], List[NonSequentialDoc]]:
        """
        Detect invoice ranges and missing serials for all document types
        
        Args:
            upload_id: Upload ID
            invoice_lines: List of invoice line dicts with invoice_no and doc_type
        
        Returns:
            (document_ranges, non_sequential_docs)
        """
        # Group by document type and prefix
        sequential_groups = defaultdict(lambda: defaultdict(list))
        non_sequential_groups = defaultdict(list)
        
        for line in invoice_lines:
            invoice_no = line.get("invoice_no_raw", line.get("invoice_no", ""))
            doc_type_str = line.get("doc_type", "tax_invoice")
            
            if not invoice_no:
                continue
            
            # Normalize
            invoice_no_norm = self.normalize_invoice_no(invoice_no)
            
            # Try to split into prefix and number
            split_result = self.split_prefix_number(invoice_no_norm)
            
            if split_result:
                prefix, number, pad_length = split_result
                # Store in sequential group
                sequential_groups[doc_type_str][prefix].append({
                    "raw": invoice_no,
                    "norm": invoice_no_norm,
                    "prefix": prefix,
                    "number": number,
                    "pad": pad_length
                })
            else:
                # Non-sequential
                non_sequential_groups[doc_type_str].append(invoice_no)
        
        # Process sequential groups to find ranges
        document_ranges = []
        
        for doc_type_str, prefix_groups in sequential_groups.items():
            for prefix, invoices in prefix_groups.items():
                # Sort by number
                invoices_sorted = sorted(invoices, key=lambda x: x["number"])
                
                if not invoices_sorted:
                    continue
                
                # Get unique numbers
                numbers = sorted(set(inv["number"] for inv in invoices_sorted))
                
                first_serial = numbers[0]
                last_serial = numbers[-1]
                found_count = len(numbers)
                expected_count = last_serial - first_serial + 1
                
                # Find missing numbers (cancelled)
                cancelled_list = []
                cancelled_ranges = []
                
                for i in range(first_serial, last_serial + 1):
                    if i not in numbers:
                        cancelled_list.append(i)
                
                # Compress cancelled list into ranges
                if cancelled_list:
                    range_start = cancelled_list[0]
                    range_end = cancelled_list[0]
                    
                    for num in cancelled_list[1:]:
                        if num == range_end + 1:
                            range_end = num
                        else:
                            cancelled_ranges.append({"start": range_start, "end": range_end})
                            range_start = num
                            range_end = num
                    
                    # Add last range
                    cancelled_ranges.append({"start": range_start, "end": range_end})
                
                # Get pad length (use most common or max)
                pad_length = max(inv["pad"] for inv in invoices_sorted)
                
                # Format doc_from and doc_to
                doc_from = self.format_serial(prefix, first_serial, pad_length)
                doc_to = self.format_serial(prefix, last_serial, pad_length)
                
                # Map doc_type string to DocumentType enum
                try:
                    doc_type = DocumentType(doc_type_str)
                except ValueError:
                    doc_type = DocumentType.TAX_INVOICE
                
                # Create DocumentRange
                doc_range = DocumentRange(
                    upload_id=upload_id,
                    doc_type=doc_type,
                    prefix=prefix,
                    first_serial=first_serial,
                    last_serial=last_serial,
                    found_count=found_count,
                    expected_count=expected_count,
                    cancelled_count=len(cancelled_list),
                    cancelled_list=cancelled_list[:100],  # Limit to first 100
                    cancelled_ranges=cancelled_ranges,
                    doc_from=doc_from,
                    doc_to=doc_to
                )
                
                document_ranges.append(doc_range)
        
        # Process non-sequential groups
        non_sequential_docs = []
        for doc_type_str, invoice_numbers in non_sequential_groups.items():
            if invoice_numbers:
                try:
                    doc_type = DocumentType(doc_type_str)
                except ValueError:
                    doc_type = DocumentType.TAX_INVOICE
                
                non_seq = NonSequentialDoc(
                    upload_id=upload_id,
                    doc_type=doc_type,
                    invoice_numbers=invoice_numbers[:50],  # Limit to first 50
                    count=len(invoice_numbers)
                )
                non_sequential_docs.append(non_seq)
        
        return document_ranges, non_sequential_docs
    
    def format_cancelled_display(self, doc_range: DocumentRange) -> str:
        """
        Format cancelled serials for display
        
        Examples:
            "INV001, INV002, INV005-INV008"
        """
        if not doc_range.cancelled_ranges:
            return "None"
        
        parts = []
        for r in doc_range.cancelled_ranges[:10]:  # Limit to 10 ranges
            start = self.format_serial(doc_range.prefix, r["start"], len(str(doc_range.last_serial)))
            end = self.format_serial(doc_range.prefix, r["end"], len(str(doc_range.last_serial)))
            
            if start == end:
                parts.append(start)
            else:
                parts.append(f"{start}-{end}")
        
        result = ", ".join(parts)
        if len(doc_range.cancelled_ranges) > 10:
            result += f" ... ({len(doc_range.cancelled_ranges) - 10} more ranges)"
        
        return result
