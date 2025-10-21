"""Schema-driven GSTR-1 generator with all sections and validation"""

from typing import List, Dict, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
import logging

from models_canonical import (
    CanonicalInvoiceLine, DocumentRange, GSTR1Export,
    GSTRSection, DocumentType
)
from decimal_utils import parse_money, round_decimal, format_for_json, ZERO
from invoice_range_detector import InvoiceRangeDetector

logger = logging.getLogger(__name__)


class SchemaDriverGSTR1Generator:
    """Generate complete GSTR-1 JSON with all sections using canonical data"""
    
    def __init__(self, gstin: str, filing_period: str, schema_version: str = "3.1.6"):
        """
        Args:
            gstin: Seller's GSTIN
            filing_period: Filing period MMYYYY (e.g., "012025")
            schema_version: Schema version (default "3.1.6")
        """
        self.gstin = gstin
        self.filing_period = filing_period
        self.schema_version = schema_version
        self.range_detector = InvoiceRangeDetector()
    
    def generate_complete_gstr1(
        self,
        invoice_lines: List[Dict],
        document_ranges: List[DocumentRange] = None
    ) -> GSTR1Export:
        """
        Generate complete GSTR-1 with all sections
        
        Returns:
            GSTR1Export with all sections populated
        """
        # Generate each section
        b2b = self.generate_b2b(invoice_lines)
        b2cl = self.generate_b2cl(invoice_lines)
        b2cs = self.generate_b2cs(invoice_lines)
        cdnr = self.generate_cdnr(invoice_lines)
        cdnur = self.generate_cdnur(invoice_lines)
        exp = self.generate_exp(invoice_lines)
        at = self.generate_at(invoice_lines)
        atadj = self.generate_atadj(invoice_lines)
        hsn = self.generate_hsn(invoice_lines)
        doc_iss = self.generate_doc_iss(document_ranges or [])
        
        # Create export
        export = GSTR1Export(
            upload_id=invoice_lines[0]["upload_id"] if invoice_lines else "",
            gstin=self.gstin,
            fp=self.filing_period,
            version=self.schema_version,
            b2b=b2b,
            b2cl=b2cl,
            b2cs=b2cs,
            cdnr=cdnr,
            cdnur=cdnur,
            exp=exp,
            at=at,
            atadj=atadj,
            hsn=hsn,
            doc_iss=doc_iss
        )
        
        # Validate and reconcile
        export.validation_warnings, export.validation_errors = self.validate_gstr1(export, invoice_lines)
        export.reconciliation_report = self.reconcile_totals(export, invoice_lines)
        
        return export
    
    def generate_b2b(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate B2B section (Registered buyers)
        
        Structure:
        [
            {
                "ctin": "29AAFCD5862R1Z5",
                "inv": [
                    {
                        "inum": "INV001",
                        "idt": "01-01-2025",
                        "val": 10000.50,
                        "pos": "29",
                        "rchrg": "N",
                        "inv_typ": "R",
                        "itms": [
                            {
                                "num": 1,
                                "itm_det": {
                                    "rt": 18,
                                    "txval": 10000.50,
                                    "iamt": 0,
                                    "camt": 900.05,
                                    "samt": 900.05,
                                    "csamt": 0
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        """
        # Filter B2B lines (registered buyers)
        b2b_lines = [
            line for line in invoice_lines
            if line.get("gstin_uin") and len(str(line.get("gstin_uin", "")).strip()) == 15
            and line.get("doc_type") == DocumentType.TAX_INVOICE.value
        ]
        
        if not b2b_lines:
            return []
        
        # Group by GSTIN (buyer)
        buyer_groups = defaultdict(list)
        for line in b2b_lines:
            ctin = str(line["gstin_uin"]).strip()
            buyer_groups[ctin].append(line)
        
        result = []
        
        for ctin, lines in buyer_groups.items():
            # Group by invoice number
            invoice_groups = defaultdict(list)
            for line in lines:
                inum = line["invoice_no_norm"]
                invoice_groups[inum].append(line)
            
            invoices = []
            for inum, inv_lines in invoice_groups.items():
                # Get invoice details from first line
                first_line = inv_lines[0]
                
                # Aggregate invoice total
                total_val = sum(parse_money(line.get("taxable_value", 0)) for line in inv_lines)
                
                # Create items (rate-wise aggregation)
                items = self._aggregate_by_rate(inv_lines)
                
                invoice = {
                    "inum": first_line["invoice_no_raw"],
                    "idt": self._format_date(first_line.get("invoice_date")),
                    "val": format_for_json(total_val),
                    "pos": first_line["place_of_supply_code"],
                    "rchrg": "Y" if first_line.get("is_reverse_charge") else "N",
                    "inv_typ": "R",  # Regular
                    "itms": items
                }
                
                invoices.append(invoice)
            
            result.append({
                "ctin": ctin,
                "inv": invoices
            })
        
        return result
    
    def generate_b2cl(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate B2CL section (Unregistered buyers with invoice value > 2.5L)
        
        Structure:
        [
            {
                "pos": "29",
                "inv": [
                    {
                        "inum": "INV001",
                        "idt": "01-01-2025",
                        "val": 300000.00,
                        "itms": [...]
                    }
                ]
            }
        ]
        """
        # Filter B2CL lines (no GSTIN, value > 2.5L)
        b2cl_lines = []
        
        # Group by invoice to check total value
        invoice_groups = defaultdict(list)
        for line in invoice_lines:
            if not line.get("gstin_uin") and line.get("doc_type") == DocumentType.TAX_INVOICE.value:
                inum = line["invoice_no_norm"]
                invoice_groups[inum].append(line)
        
        # Filter invoices with total > 2.5L
        for inum, lines in invoice_groups.items():
            total_val = sum(parse_money(line.get("taxable_value", 0)) for line in lines)
            if total_val > Decimal("250000"):
                b2cl_lines.extend(lines)
        
        if not b2cl_lines:
            return []
        
        # Group by state
        state_groups = defaultdict(list)
        for line in b2cl_lines:
            pos = line["place_of_supply_code"]
            state_groups[pos].append(line)
        
        result = []
        
        for pos, lines in state_groups.items():
            # Group by invoice
            invoice_groups = defaultdict(list)
            for line in lines:
                inum = line["invoice_no_norm"]
                invoice_groups[inum].append(line)
            
            invoices = []
            for inum, inv_lines in invoice_groups.items():
                first_line = inv_lines[0]
                total_val = sum(parse_money(line.get("taxable_value", 0)) for line in inv_lines)
                items = self._aggregate_by_rate(inv_lines)
                
                invoice = {
                    "inum": first_line["invoice_no_raw"],
                    "idt": self._format_date(first_line.get("invoice_date")),
                    "val": format_for_json(total_val),
                    "itms": items
                }
                
                invoices.append(invoice)
            
            result.append({
                "pos": pos,
                "inv": invoices
            })
        
        return result
    
    def generate_b2cs(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate B2CS section (Table 7 - B2C Small)
        
        Structure:
        [
            {
                "pos": "29",
                "rt": 18,
                "typ": "E",  # E-commerce
                "txval": 10000.50,
                "iamt": 0,
                "camt": 900.05,
                "samt": 900.05,
                "csamt": 0
            }
        ]
        """
        # Filter B2CS lines (no GSTIN, value <= 2.5L)
        b2cs_lines = []
        
        # Group by invoice to check total value
        invoice_groups = defaultdict(list)
        for line in invoice_lines:
            if not line.get("gstin_uin") and line.get("doc_type") == DocumentType.TAX_INVOICE.value:
                inum = line["invoice_no_norm"]
                invoice_groups[inum].append(line)
        
        # Filter invoices with total <= 2.5L
        for inum, lines in invoice_groups.items():
            total_val = sum(parse_money(line.get("taxable_value", 0)) for line in lines)
            if total_val <= Decimal("250000"):
                b2cs_lines.extend(lines)
        
        if not b2cs_lines:
            return []
        
        # Group by (state, rate, type)
        aggregation = defaultdict(lambda: {
            "txval": ZERO,
            "iamt": ZERO,
            "camt": ZERO,
            "samt": ZERO,
            "csamt": ZERO
        })
        
        for line in b2cs_lines:
            pos = line["place_of_supply_code"]
            rt = float(line["gst_rate"])
            typ = "E" if line.get("origin") == "meesho" else "OE"  # E = E-commerce
            
            key = (pos, rt, typ)
            
            computed_tax = line.get("computed_tax", {})
            aggregation[key]["txval"] += parse_money(line.get("taxable_value", 0))
            aggregation[key]["iamt"] += parse_money(computed_tax.get("igst_amount", 0))
            aggregation[key]["camt"] += parse_money(computed_tax.get("cgst_amount", 0))
            aggregation[key]["samt"] += parse_money(computed_tax.get("sgst_amount", 0))
        
        # Format output
        result = []
        for (pos, rt, typ), totals in aggregation.items():
            result.append({
                "pos": pos,
                "rt": rt,
                "typ": typ,
                "txval": format_for_json(totals["txval"]),
                "iamt": format_for_json(totals["iamt"]),
                "camt": format_for_json(totals["camt"]),
                "samt": format_for_json(totals["samt"]),
                "csamt": format_for_json(totals["csamt"])
            })
        
        # Sort by state and rate
        result.sort(key=lambda x: (x["pos"], x["rt"]))
        
        return result
    
    def generate_cdnr(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate CDNR section (Credit/Debit Notes - Registered)
        
        Structure similar to B2B but for notes
        """
        cdnr_lines = [
            line for line in invoice_lines
            if line.get("gstin_uin") and len(str(line.get("gstin_uin", "")).strip()) == 15
            and line.get("doc_type") in [DocumentType.CREDIT_NOTE.value, DocumentType.DEBIT_NOTE.value]
        ]
        
        if not cdnr_lines:
            return []
        
        # Similar structure to B2B
        # Group by GSTIN
        buyer_groups = defaultdict(list)
        for line in cdnr_lines:
            ctin = str(line["gstin_uin"]).strip()
            buyer_groups[ctin].append(line)
        
        result = []
        
        for ctin, lines in buyer_groups.items():
            notes = []
            
            for line in lines:
                note_type = "C" if line["doc_type"] == DocumentType.CREDIT_NOTE.value else "D"
                items = self._aggregate_by_rate([line])
                
                note = {
                    "nt_num": line["invoice_no_raw"],
                    "nt_dt": self._format_date(line.get("invoice_date")),
                    "ntty": note_type,
                    "pos": line["place_of_supply_code"],
                    "rchrg": "N",
                    "val": format_for_json(parse_money(line.get("taxable_value", 0))),
                    "itms": items
                }
                
                notes.append(note)
            
            result.append({
                "ctin": ctin,
                "nt": notes
            })
        
        return result
    
    def generate_cdnur(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate CDNUR section (Credit/Debit Notes - Unregistered)
        """
        cdnur_lines = [
            line for line in invoice_lines
            if not line.get("gstin_uin")
            and line.get("doc_type") in [DocumentType.CREDIT_NOTE.value, DocumentType.DEBIT_NOTE.value]
        ]
        
        if not cdnur_lines:
            return []
        
        result = []
        
        for line in cdnur_lines:
            note_type = "C" if line["doc_type"] == DocumentType.CREDIT_NOTE.value else "D"
            items = self._aggregate_by_rate([line])
            
            note = {
                "nt_num": line["invoice_no_raw"],
                "nt_dt": self._format_date(line.get("invoice_date")),
                "ntty": note_type,
                "pos": line["place_of_supply_code"],
                "typ": "E" if line.get("origin") == "meesho" else "OE",
                "val": format_for_json(parse_money(line.get("taxable_value", 0))),
                "itms": items
            }
            
            result.append(note)
        
        return result
    
    def generate_exp(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate EXP section (Exports)
        
        Currently returns empty as Meesho doesn't have exports
        """
        return []
    
    def generate_at(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate AT section (Advance Tax)
        
        Currently returns empty
        """
        return []
    
    def generate_atadj(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate ATADJ section (Advance Tax Adjustments)
        
        Currently returns empty
        """
        return []
    
    def generate_hsn(self, invoice_lines: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate HSN section (HSN Summary)
        
        Structure:
        [
            {
                "num": 1,
                "hsn_sc": "1234",
                "desc": "Description",
                "uqc": "PCS",
                "qty": 100,
                "val": 10000.50,
                "txval": 10000.50,
                "iamt": 0,
                "camt": 900.05,
                "samt": 900.05,
                "csamt": 0
            }
        ]
        """
        hsn_lines = [line for line in invoice_lines if line.get("hsn_code")]
        
        if not hsn_lines:
            return []
        
        # Group by HSN code
        hsn_groups = defaultdict(lambda: {
            "desc": "",
            "uqc": "",
            "qty": ZERO,
            "val": ZERO,
            "txval": ZERO,
            "iamt": ZERO,
            "camt": ZERO,
            "samt": ZERO,
            "csamt": ZERO
        })
        
        for line in hsn_lines:
            hsn = str(line["hsn_code"]).strip()
            computed_tax = line.get("computed_tax", {})
            
            if not hsn_groups[hsn]["desc"] and line.get("description"):
                hsn_groups[hsn]["desc"] = line["description"]
            if not hsn_groups[hsn]["uqc"] and line.get("uqc"):
                hsn_groups[hsn]["uqc"] = line["uqc"]
            
            hsn_groups[hsn]["qty"] += parse_money(line.get("quantity", 0))
            val = parse_money(line.get("taxable_value", 0))
            hsn_groups[hsn]["val"] += val
            hsn_groups[hsn]["txval"] += val
            hsn_groups[hsn]["iamt"] += parse_money(computed_tax.get("igst_amount", 0))
            hsn_groups[hsn]["camt"] += parse_money(computed_tax.get("cgst_amount", 0))
            hsn_groups[hsn]["samt"] += parse_money(computed_tax.get("sgst_amount", 0))
        
        result = []
        for num, (hsn_sc, totals) in enumerate(sorted(hsn_groups.items()), start=1):
            result.append({
                "num": num,
                "hsn_sc": hsn_sc,
                "desc": totals["desc"] or "",
                "uqc": totals["uqc"] or "OTH",
                "qty": format_for_json(totals["qty"]),
                "val": format_for_json(totals["val"]),
                "txval": format_for_json(totals["txval"]),
                "iamt": format_for_json(totals["iamt"]),
                "camt": format_for_json(totals["camt"]),
                "samt": format_for_json(totals["samt"]),
                "csamt": format_for_json(totals["csamt"])
            })
        
        return result
    
    def generate_doc_iss(self, document_ranges: List[DocumentRange]) -> List[Dict[str, Any]]:
        """
        Generate DOC_ISS section (Table 13 - Documents Issued)
        
        Structure:
        [
            {
                "doc_num": 1,
                "doc_typ": "Invoices for outward supply",
                "docs": [
                    {
                        "num": 1,
                        "from": "INV001",
                        "to": "INV050",
                        "totnum": 45,
                        "cancel": 5,
                        "net_issue": 45
                    }
                ]
            }
        ]
        """
        if not document_ranges:
            return []
        
        # Group by document type
        doc_type_groups = defaultdict(list)
        for doc_range in document_ranges:
            doc_type = self._map_doc_type_to_portal(doc_range.doc_type)
            doc_type_groups[doc_type].append(doc_range)
        
        result = []
        doc_num = 1
        
        # Order: Invoices, Credit Notes, Debit Notes, Delivery Challans, etc.
        doc_type_order = [
            "Invoices for outward supply",
            "Credit Notes",
            "Debit Notes", 
            "Delivery Challans",
            "Refund Vouchers",
            "Receipt Vouchers"
        ]
        
        for doc_typ in doc_type_order:
            if doc_typ not in doc_type_groups:
                continue
            
            docs = []
            for num, doc_range in enumerate(doc_type_groups[doc_typ], start=1):
                docs.append({
                    "num": num,
                    "from": doc_range.doc_from,
                    "to": doc_range.doc_to,
                    "totnum": doc_range.found_count,
                    "cancel": doc_range.cancelled_count,
                    "net_issue": doc_range.found_count
                })
            
            result.append({
                "doc_num": doc_num,
                "doc_typ": doc_typ,
                "docs": docs
            })
            
            doc_num += 1
        
        return result
    
    def _aggregate_by_rate(self, lines: List[Dict]) -> List[Dict[str, Any]]:
        """Aggregate invoice lines by GST rate"""
        rate_groups = defaultdict(lambda: {
            "txval": ZERO,
            "iamt": ZERO,
            "camt": ZERO,
            "samt": ZERO,
            "csamt": ZERO
        })
        
        for line in lines:
            rt = float(line["gst_rate"])
            computed_tax = line.get("computed_tax", {})
            
            rate_groups[rt]["txval"] += parse_money(line.get("taxable_value", 0))
            rate_groups[rt]["iamt"] += parse_money(computed_tax.get("igst_amount", 0))
            rate_groups[rt]["camt"] += parse_money(computed_tax.get("cgst_amount", 0))
            rate_groups[rt]["samt"] += parse_money(computed_tax.get("sgst_amount", 0))
        
        items = []
        for num, (rt, totals) in enumerate(sorted(rate_groups.items()), start=1):
            items.append({
                "num": num,
                "itm_det": {
                    "rt": rt,
                    "txval": format_for_json(totals["txval"]),
                    "iamt": format_for_json(totals["iamt"]),
                    "camt": format_for_json(totals["camt"]),
                    "samt": format_for_json(totals["samt"]),
                    "csamt": format_for_json(totals["csamt"])
                }
            })
        
        return items
    
    def _format_date(self, date_value: str) -> str:
        """Format date to DD-MM-YYYY"""
        if not date_value:
            return ""
        
        try:
            # Assume ISO format YYYY-MM-DD
            parts = date_value.split("-")
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            pass
        
        return date_value
    
    def _map_doc_type_to_portal(self, doc_type: DocumentType) -> str:
        """Map internal document type to portal nomenclature"""
        mapping = {
            DocumentType.TAX_INVOICE: "Invoices for outward supply",
            DocumentType.CREDIT_NOTE: "Credit Notes",
            DocumentType.DEBIT_NOTE: "Debit Notes",
            DocumentType.DELIVERY_CHALLAN: "Delivery Challans",
            DocumentType.REFUND_VOUCHER: "Refund Vouchers",
            DocumentType.RECEIPT_VOUCHER: "Receipt Vouchers"
        }
        return mapping.get(doc_type, "Invoices for outward supply")
    
    def validate_gstr1(
        self,
        export: GSTR1Export,
        invoice_lines: List[Dict]
    ) -> Tuple[List[str], List[str]]:
        """
        Validate GSTR-1 export
        
        Returns:
            (warnings, errors)
        """
        warnings = []
        errors = []
        
        # Required top-level fields
        if not export.gstin:
            errors.append("GSTIN is required")
        if not export.fp:
            errors.append("Filing period is required")
        
        # Check if any data present
        has_data = any([
            export.b2b, export.b2cl, export.b2cs,
            export.cdnr, export.cdnur, export.hsn, export.doc_iss
        ])
        
        if not has_data:
            warnings.append("No data found in any section")
        
        # Validate B2CS entries
        for entry in export.b2cs:
            if entry.get("txval", 0) <= 0:
                warnings.append(f"B2CS entry with zero or negative taxable value: {entry}")
        
        return warnings, errors
    
    def reconcile_totals(
        self,
        export: GSTR1Export,
        invoice_lines: List[Dict]
    ) -> Dict[str, Any]:
        """
        Reconcile totals across sections
        
        Returns:
            Reconciliation report
        """
        # Calculate totals from invoice lines
        total_lines_txval = sum(parse_money(line.get("taxable_value", 0)) for line in invoice_lines)
        total_lines_tax = sum(
            parse_money(line.get("computed_tax", {}).get("tax_amount", 0))
            for line in invoice_lines
        )
        
        # Calculate totals from B2CS
        total_b2cs_txval = sum(
            parse_money(entry.get("txval", 0))
            for entry in export.b2cs
        )
        
        total_b2cs_tax = sum(
            parse_money(entry.get("iamt", 0)) + 
            parse_money(entry.get("camt", 0)) + 
            parse_money(entry.get("samt", 0))
            for entry in export.b2cs
        )
        
        # Check differences
        txval_diff = abs(total_lines_txval - total_b2cs_txval)
        tax_diff = abs(total_lines_tax - total_b2cs_tax)
        
        report = {
            "invoice_lines": {
                "taxable_value": format_for_json(total_lines_txval),
                "tax": format_for_json(total_lines_tax)
            },
            "b2cs_section": {
                "taxable_value": format_for_json(total_b2cs_txval),
                "tax": format_for_json(total_b2cs_tax)
            },
            "differences": {
                "taxable_value": format_for_json(txval_diff),
                "tax": format_for_json(tax_diff)
            },
            "reconciled": txval_diff < Decimal("0.50") and tax_diff < Decimal("0.50")
        }
        
        return report
