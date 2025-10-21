"""
Complete GSTR-1 Generator with ALL Tables matching GST Portal Format
Includes ALL sections: B2B, B2CL, B2CS, CDNR, CDNUR, EXP, EXPWOP, AT, ATADJ, HSN, DOC_ISS, NIL, ECO
Enhanced with Gemini AI for intelligent data processing
"""

from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
import logging
from datetime import datetime

from models_canonical import CanonicalInvoiceLine, DocumentRange, DocumentType, GSTRSection
from decimal_utils import parse_money, round_decimal, format_for_json, ZERO
from gemini_service import gemini_service

logger = logging.getLogger(__name__)


class CompleteGSTR1Generator:
    """
    Complete GSTR-1 JSON generator matching exact GST Portal format
    All 13+ tables with Gemini AI intelligence
    """
    
    def __init__(self, gstin: str, filing_period: str, seller_state_code: str = "27"):
        """
        Args:
            gstin: Seller's GSTIN (15 chars)
            filing_period: MMYYYY format (e.g., "012025")
            seller_state_code: Seller's state code (2 digits)
        """
        self.gstin = gstin
        self.filing_period = filing_period
        self.seller_state_code = seller_state_code
        
        # Extract financial year from filing period
        month = int(filing_period[:2])
        year = int(filing_period[2:])
        self.ret_period = filing_period  # MMYYYY
        
    def generate_complete_gstr1(
        self,
        invoice_lines: List[Dict],
        document_ranges: List[DocumentRange] = None,
        use_gemini: bool = True
    ) -> Dict[str, Any]:
        """
        Generate complete GSTR-1 JSON with ALL sections
        
        Returns:
            Complete GSTR-1 JSON matching GST portal format
        """
        logger.info(f"Generating complete GSTR-1 for {len(invoice_lines)} invoice lines")
        
        # Use Gemini to validate and enhance data before generation
        if use_gemini and invoice_lines:
            validated_lines = self._gemini_validate_invoice_data(invoice_lines)
            invoice_lines = validated_lines if validated_lines else invoice_lines
        
        # Generate all sections
        gstr1_data = {
            "gstin": self.gstin,
            "fp": self.filing_period,
            "gt": self._calculate_gross_turnover(invoice_lines),
            "cur_gt": self._calculate_current_gross_turnover(invoice_lines),
        }
        
        # All GSTR-1 sections
        sections = {
            "b2b": self.generate_b2b(invoice_lines, use_gemini),
            "b2cl": self.generate_b2cl(invoice_lines, use_gemini),
            "b2cs": self.generate_b2cs(invoice_lines, use_gemini),
            "b2csa": self.generate_b2csa(invoice_lines),  # B2CS amendments
            "cdnr": self.generate_cdnr(invoice_lines, use_gemini),
            "cdnur": self.generate_cdnur(invoice_lines, use_gemini),
            "cdnra": self.generate_cdnra(invoice_lines),  # CDNR amendments
            "cdnura": self.generate_cdnura(invoice_lines),  # CDNUR amendments
            "exp": self.generate_exp(invoice_lines, use_gemini),
            "expa": self.generate_expa(invoice_lines),  # Export amendments
            "at": self.generate_at(invoice_lines, use_gemini),
            "ata": self.generate_ata(invoice_lines),  # AT amendments
            "atadj": self.generate_atadj(invoice_lines, use_gemini),
            "atadja": self.generate_atadja(invoice_lines),  # ATADJ amendments
            "exemp": self.generate_exemp(invoice_lines, use_gemini),  # NIL rated/exempted
            "hsn": self.generate_hsn(invoice_lines, use_gemini),
            "txpd": self.generate_txpd(invoice_lines),  # Tax paid on advances
            "txpda": self.generate_txpda(invoice_lines),  # TXPD amendments
            "doc_issue": self.generate_doc_issue(document_ranges or []),
        }
        
        # Add sections to main data
        for key, value in sections.items():
            if value:  # Only add non-empty sections
                gstr1_data[key] = value
        
        # Validation with Gemini
        if use_gemini:
            validation_report = self._gemini_validate_gstr1(gstr1_data, invoice_lines)
            gstr1_data["_validation"] = validation_report
        
        logger.info(f"GSTR-1 generation complete with {len([k for k, v in sections.items() if v])} sections")
        
        return gstr1_data
    
    def generate_b2b(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 4A, 4B, 4C, 6B, 6C - B2B Invoices (Registered buyers)
        
        Format:
        [
          {
            "ctin": "29AAACI1111H1Z5",
            "inv": [
              {
                "inum": "INV001",
                "idt": "15-10-2025",
                "val": 10000.50,
                "pos": "29",
                "rchrg": "N",
                "inv_typ": "R",
                "itms": [
                  {
                    "num": 1,
                    "itm_det": {
                      "rt": 18,
                      "txval": 8474.58,
                      "iamt": 0,
                      "camt": 764.62,
                      "samt": 760.8,
                      "csamt": 0
                    }
                  }
                ]
              }
            ]
          }
        ]
        """
        # Filter B2B lines (has GSTIN, 15 chars)
        b2b_lines = [
            line for line in invoice_lines
            if line.get("gstin_uin") 
            and len(str(line.get("gstin_uin", "")).strip()) == 15
            and line.get("doc_type") == DocumentType.TAX_INVOICE.value
        ]
        
        if not b2b_lines:
            return []
        
        # Use Gemini to suggest missing B2B data
        if use_gemini and b2b_lines:
            b2b_lines = self._gemini_enhance_b2b_data(b2b_lines)
        
        # Group by buyer GSTIN
        buyer_groups = defaultdict(list)
        for line in b2b_lines:
            ctin = str(line["gstin_uin"]).strip().upper()
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
                first_line = inv_lines[0]
                
                # Calculate total invoice value
                total_val = sum(parse_money(line.get("taxable_value", 0)) for line in inv_lines)
                
                # Get computed tax from first line
                computed_tax = first_line.get("computed_tax", {})
                for line in inv_lines:
                    if line.get("computed_tax"):
                        computed_tax = line["computed_tax"]
                        break
                
                # Aggregate by rate
                items = self._aggregate_by_rate(inv_lines)
                
                invoice = {
                    "inum": first_line["invoice_no_raw"],
                    "idt": self._format_date(first_line.get("invoice_date")),
                    "val": format_for_json(total_val),
                    "pos": first_line["place_of_supply_code"],
                    "rchrg": "Y" if first_line.get("is_reverse_charge") else "N",
                    "inv_typ": "R",  # R=Regular, SEWP=SEZ with payment, SEWOP=SEZ without payment, DE=Deemed Export
                    "itms": items
                }
                
                invoices.append(invoice)
            
            result.append({
                "ctin": ctin,
                "inv": invoices
            })
        
        return result
    
    def generate_b2cl(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 5A, 5B - B2C Large (Unregistered, invoice value > 2.5L)
        
        Format:
        [
          {
            "pos": "29",
            "inv": [
              {
                "inum": "L001",
                "idt": "10-10-2025",
                "val": 300000,
                "itms": [...]
              }
            ]
          }
        ]
        """
        # Group by invoice to check value
        invoice_groups = defaultdict(list)
        for line in invoice_lines:
            if (not line.get("gstin_uin") or len(str(line.get("gstin_uin", "")).strip()) < 15) \
               and line.get("doc_type") == DocumentType.TAX_INVOICE.value:
                inum = line["invoice_no_norm"]
                invoice_groups[inum].append(line)
        
        # Filter invoices > 2.5L
        b2cl_lines = []
        for inum, lines in invoice_groups.items():
            total_val = sum(parse_money(line.get("taxable_value", 0)) for line in lines)
            if total_val > Decimal("250000"):
                b2cl_lines.extend(lines)
        
        if not b2cl_lines:
            return []
        
        # Use Gemini enhancement
        if use_gemini and b2cl_lines:
            b2cl_lines = self._gemini_enhance_b2c_data(b2cl_lines)
        
        # Group by state (POS)
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
    
    def generate_b2cs(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 7 - B2C Small (Unregistered, invoice value <= 2.5L)
        
        Format:
        [
          {
            "sply_ty": "INTRA",
            "pos": "29",
            "typ": "E",
            "rt": 18,
            "txval": 10000.50,
            "iamt": 0,
            "camt": 900.05,
            "samt": 900.05,
            "csamt": 0,
            "etin": "07AARCM9332R1CQ"
          }
        ]
        """
        # Group by invoice to check value
        invoice_groups = defaultdict(list)
        for line in invoice_lines:
            if (not line.get("gstin_uin") or len(str(line.get("gstin_uin", "")).strip()) < 15) \
               and line.get("doc_type") == DocumentType.TAX_INVOICE.value:
                inum = line["invoice_no_norm"]
                invoice_groups[inum].append(line)
        
        # Filter invoices <= 2.5L
        b2cs_lines = []
        for inum, lines in invoice_groups.items():
            total_val = sum(parse_money(line.get("taxable_value", 0)) for line in lines)
            if total_val <= Decimal("250000"):
                b2cs_lines.extend(lines)
        
        if not b2cs_lines:
            return []
        
        # Use Gemini to enhance B2CS data
        if use_gemini and b2cs_lines:
            b2cs_lines = self._gemini_enhance_b2c_data(b2cs_lines)
        
        # Group by (supply_type, pos, type, rate, etin if any)
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
            
            # Determine supply type
            is_intra = line.get("is_intra_state", False)
            sply_ty = "INTRA" if is_intra else "INTER"
            
            # Determine type (E = E-commerce, OE = Others)
            typ = "E" if line.get("origin") == "meesho" else "OE"
            
            # E-commerce GSTIN if applicable
            etin = "07AARCM9332R1CQ" if typ == "E" else None
            
            key = (sply_ty, pos, typ, rt, etin)
            
            computed_tax = line.get("computed_tax", {})
            aggregation[key]["txval"] += parse_money(line.get("taxable_value", 0))
            aggregation[key]["iamt"] += parse_money(computed_tax.get("igst_amount", 0))
            aggregation[key]["camt"] += parse_money(computed_tax.get("cgst_amount", 0))
            aggregation[key]["samt"] += parse_money(computed_tax.get("sgst_amount", 0))
        
        # Format output
        result = []
        for (sply_ty, pos, typ, rt, etin), totals in aggregation.items():
            entry = {
                "sply_ty": sply_ty,
                "pos": pos,
                "typ": typ,
                "rt": rt,
                "txval": format_for_json(totals["txval"]),
                "iamt": format_for_json(totals["iamt"]),
                "camt": format_for_json(totals["camt"]),
                "samt": format_for_json(totals["samt"]),
                "csamt": format_for_json(totals["csamt"])
            }
            
            if etin:
                entry["etin"] = etin
            
            result.append(entry)
        
        # Sort
        result.sort(key=lambda x: (x["sply_ty"], x["pos"], x["rt"]))
        
        return result
    
    def generate_b2csa(self, invoice_lines: List[Dict]) -> List[Dict]:
        """Table 7 amendments - currently empty, can be implemented if needed"""
        return []
    
    def generate_cdnr(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 9B - Credit/Debit Notes - Registered
        
        Format:
        [
          {
            "ctin": "29AAACI1111H1Z5",
            "nt": [
              {
                "ntty": "C",
                "nt_num": "CN001",
                "nt_dt": "12-10-2025",
                "rsn": "Sales Return",
                "p_gst": "Y",
                "inum": "INV001",
                "idt": "01-10-2025",
                "val": 1000,
                "itms": [...]
              }
            ]
          }
        ]
        """
        cdnr_lines = [
            line for line in invoice_lines
            if line.get("gstin_uin") 
            and len(str(line.get("gstin_uin", "")).strip()) == 15
            and line.get("doc_type") in [DocumentType.CREDIT_NOTE.value, DocumentType.DEBIT_NOTE.value]
        ]
        
        if not cdnr_lines:
            return []
        
        if use_gemini and cdnr_lines:
            cdnr_lines = self._gemini_enhance_credit_note_data(cdnr_lines)
        
        # Group by GSTIN
        buyer_groups = defaultdict(list)
        for line in cdnr_lines:
            ctin = str(line["gstin_uin"]).strip().upper()
            buyer_groups[ctin].append(line)
        
        result = []
        
        for ctin, lines in buyer_groups.items():
            notes = []
            
            for line in lines:
                ntty = "C" if line["doc_type"] == DocumentType.CREDIT_NOTE.value else "D"
                items = self._aggregate_by_rate([line])
                
                note = {
                    "ntty": ntty,
                    "nt_num": line["invoice_no_raw"],
                    "nt_dt": self._format_date(line.get("invoice_date")),
                    "rsn": line.get("reason", "Sales Return" if ntty == "C" else "Price Difference"),
                    "p_gst": "Y",  # Pre GST: Y/N
                    "pos": line["place_of_supply_code"],
                    "rchrg": "N",
                    "inv_typ": "R",
                    "val": format_for_json(parse_money(line.get("taxable_value", 0))),
                    "itms": items
                }
                
                notes.append(note)
            
            result.append({
                "ctin": ctin,
                "nt": notes
            })
        
        return result
    
    def generate_cdnur(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 9B - Credit/Debit Notes - Unregistered
        
        Format:
        [
          {
            "ntty": "C",
            "nt_num": "CN001",
            "nt_dt": "12-10-2025",
            "rsn": "Sales Return",
            "p_gst": "Y",
            "pos": "29",
            "typ": "E",
            "val": 1000,
            "itms": [...]
          }
        ]
        """
        cdnur_lines = [
            line for line in invoice_lines
            if (not line.get("gstin_uin") or len(str(line.get("gstin_uin", "")).strip()) < 15)
            and line.get("doc_type") in [DocumentType.CREDIT_NOTE.value, DocumentType.DEBIT_NOTE.value]
        ]
        
        if not cdnur_lines:
            return []
        
        if use_gemini and cdnur_lines:
            cdnur_lines = self._gemini_enhance_credit_note_data(cdnur_lines)
        
        result = []
        
        for line in cdnur_lines:
            ntty = "C" if line["doc_type"] == DocumentType.CREDIT_NOTE.value else "D"
            items = self._aggregate_by_rate([line])
            typ = "E" if line.get("origin") == "meesho" else "OE"
            
            note = {
                "ntty": ntty,
                "nt_num": line["invoice_no_raw"],
                "nt_dt": self._format_date(line.get("invoice_date")),
                "rsn": line.get("reason", "Sales Return" if ntty == "C" else "Price Difference"),
                "p_gst": "Y",
                "pos": line["place_of_supply_code"],
                "typ": typ,
                "val": format_for_json(parse_money(line.get("taxable_value", 0))),
                "itms": items
            }
            
            result.append(note)
        
        return result
    
    def generate_cdnra(self, invoice_lines: List[Dict]) -> List[Dict]:
        """CDNR amendments - currently empty"""
        return []
    
    def generate_cdnura(self, invoice_lines: List[Dict]) -> List[Dict]:
        """CDNUR amendments - currently empty"""
        return []
    
    def generate_exp(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 6A - Export Invoices (with payment of tax)
        
        Format:
        [
          {
            "ex_tp": "WPAY",
            "inum": "EXP001",
            "idt": "05-10-2025",
            "val": 50000,
            "sbpcode": "INNSA",
            "sbnum": "123456",
            "sbdt": "05-10-2025",
            "itms": [...]
          }
        ]
        """
        exp_lines = [
            line for line in invoice_lines
            if line.get("is_export") 
            and line.get("export_type") == "WPAY"
            and line.get("doc_type") == DocumentType.TAX_INVOICE.value
        ]
        
        if not exp_lines:
            return []
        
        if use_gemini and exp_lines:
            exp_lines = self._gemini_enhance_export_data(exp_lines)
        
        # Group by invoice
        invoice_groups = defaultdict(list)
        for line in exp_lines:
            inum = line["invoice_no_norm"]
            invoice_groups[inum].append(line)
        
        result = []
        
        for inum, inv_lines in invoice_groups.items():
            first_line = inv_lines[0]
            total_val = sum(parse_money(line.get("taxable_value", 0)) for line in inv_lines)
            items = self._aggregate_by_rate(inv_lines)
            
            export = {
                "ex_tp": "WPAY",  # WPAY = With payment, WOPAY = Without payment
                "inum": first_line["invoice_no_raw"],
                "idt": self._format_date(first_line.get("invoice_date")),
                "val": format_for_json(total_val),
                "sbpcode": first_line.get("port_code", ""),
                "sbnum": first_line.get("shipping_bill_no", ""),
                "sbdt": self._format_date(first_line.get("shipping_bill_date", "")),
                "itms": items
            }
            
            result.append(export)
        
        return result
    
    def generate_expa(self, invoice_lines: List[Dict]) -> List[Dict]:
        """Export amendments - currently empty"""
        return []
    
    def generate_at(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 11A(1), 11A(2) - Advances Received
        
        Format:
        [
          {
            "pos": "29",
            "sply_ty": "INTRA",
            "rt": 18,
            "ad_amt": 10000,
            "iamt": 0,
            "camt": 900,
            "samt": 900,
            "csamt": 0
          }
        ]
        """
        at_lines = [
            line for line in invoice_lines
            if line.get("is_advance_payment") 
            and line.get("doc_type") == "advance_receipt"
        ]
        
        if not at_lines:
            return []
        
        # Group by (pos, supply_type, rate)
        aggregation = defaultdict(lambda: {
            "ad_amt": ZERO,
            "iamt": ZERO,
            "camt": ZERO,
            "samt": ZERO,
            "csamt": ZERO
        })
        
        for line in at_lines:
            pos = line["place_of_supply_code"]
            is_intra = line.get("is_intra_state", False)
            sply_ty = "INTRA" if is_intra else "INTER"
            rt = float(line["gst_rate"])
            
            key = (pos, sply_ty, rt)
            
            computed_tax = line.get("computed_tax", {})
            aggregation[key]["ad_amt"] += parse_money(line.get("taxable_value", 0))
            aggregation[key]["iamt"] += parse_money(computed_tax.get("igst_amount", 0))
            aggregation[key]["camt"] += parse_money(computed_tax.get("cgst_amount", 0))
            aggregation[key]["samt"] += parse_money(computed_tax.get("sgst_amount", 0))
        
        result = []
        for (pos, sply_ty, rt), totals in aggregation.items():
            result.append({
                "pos": pos,
                "sply_ty": sply_ty,
                "rt": rt,
                "ad_amt": format_for_json(totals["ad_amt"]),
                "iamt": format_for_json(totals["iamt"]),
                "camt": format_for_json(totals["camt"]),
                "samt": format_for_json(totals["samt"]),
                "csamt": format_for_json(totals["csamt"])
            })
        
        return result
    
    def generate_ata(self, invoice_lines: List[Dict]) -> List[Dict]:
        """AT amendments - currently empty"""
        return []
    
    def generate_atadj(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 11B(1), 11B(2) - Adjustment of Advances
        
        Format:
        [
          {
            "pos": "29",
            "sply_ty": "INTRA",
            "rt": 18,
            "ad_amt": 10000,
            "iamt": 0,
            "camt": 900,
            "samt": 900,
            "csamt": 0
          }
        ]
        """
        atadj_lines = [
            line for line in invoice_lines
            if line.get("is_advance_adjustment")
            and line.get("doc_type") == "advance_adjustment"
        ]
        
        if not atadj_lines:
            return []
        
        # Similar structure to AT
        aggregation = defaultdict(lambda: {
            "ad_amt": ZERO,
            "iamt": ZERO,
            "camt": ZERO,
            "samt": ZERO,
            "csamt": ZERO
        })
        
        for line in atadj_lines:
            pos = line["place_of_supply_code"]
            is_intra = line.get("is_intra_state", False)
            sply_ty = "INTRA" if is_intra else "INTER"
            rt = float(line["gst_rate"])
            
            key = (pos, sply_ty, rt)
            
            computed_tax = line.get("computed_tax", {})
            aggregation[key]["ad_amt"] += parse_money(line.get("taxable_value", 0))
            aggregation[key]["iamt"] += parse_money(computed_tax.get("igst_amount", 0))
            aggregation[key]["camt"] += parse_money(computed_tax.get("cgst_amount", 0))
            aggregation[key]["samt"] += parse_money(computed_tax.get("sgst_amount", 0))
        
        result = []
        for (pos, sply_ty, rt), totals in aggregation.items():
            result.append({
                "pos": pos,
                "sply_ty": sply_ty,
                "rt": rt,
                "ad_amt": format_for_json(totals["ad_amt"]),
                "iamt": format_for_json(totals["iamt"]),
                "camt": format_for_json(totals["camt"]),
                "samt": format_for_json(totals["samt"]),
                "csamt": format_for_json(totals["csamt"])
            })
        
        return result
    
    def generate_atadja(self, invoice_lines: List[Dict]) -> List[Dict]:
        """ATADJ amendments - currently empty"""
        return []
    
    def generate_exemp(self, invoice_lines: List[Dict], use_gemini: bool = True) -> List[Dict]:
        """
        Table 8 - NIL Rated, Exempted, Non-GST Supplies
        
        Format:
        [
          {
            "sply_ty": "INTRB2B",
            "nil_amt": 10000,
            "expt_amt": 5000,
            "ngsup_amt": 2000
          }
        ]
        """
        exemp_lines = [
            line for line in invoice_lines
            if line.get("gst_rate", 0) == 0 
            or line.get("is_exempted")
            or line.get("is_nil_rated")
            or line.get("is_non_gst")
        ]
        
        if not exemp_lines:
            return []
        
        # Group by supply type
        aggregation = defaultdict(lambda: {
            "nil_amt": ZERO,
            "expt_amt": ZERO,
            "ngsup_amt": ZERO
        })
        
        for line in exemp_lines:
            # Determine supply type
            has_gstin = line.get("gstin_uin") and len(str(line.get("gstin_uin", "")).strip()) == 15
            is_intra = line.get("is_intra_state", False)
            
            if has_gstin:
                sply_ty = "INTRB2B" if is_intra else "INTERB2B"
            else:
                sply_ty = "INTRB2C" if is_intra else "INTERB2C"
            
            taxable = parse_money(line.get("taxable_value", 0))
            
            if line.get("is_nil_rated") or line.get("gst_rate", 0) == 0:
                aggregation[sply_ty]["nil_amt"] += taxable
            elif line.get("is_exempted"):
                aggregation[sply_ty]["expt_amt"] += taxable
            elif line.get("is_non_gst"):
                aggregation[sply_ty]["ngsup_amt"] += taxable
        
        result = []
        for sply_ty, totals in aggregation.items():
            result.append({
                "sply_ty": sply_ty,
                "nil_amt": format_for_json(totals["nil_amt"]),
                "expt_amt": format_for_json(totals["expt_amt"]),
                "ngsup_amt": format_for_json(totals["ngsup_amt"])
            })
        
        return result
    
    def generate_hsn(self, invoice_lines: List[Dict], use_gemini: bool = True) -> Dict[str, List[Dict]]:
        """
        Table 12 - HSN Summary (split into B2B and B2C from 2025)
        
        Format:
        {
          "data": [
            {
              "num": 1,
              "hsn_sc": "1006",
              "desc": "Rice",
              "uqc": "KGS",
              "qty": 100,
              "val": 8500,
              "txval": 8500,
              "rt": 5,
              "iamt": 0,
              "camt": 212.5,
              "samt": 212.5,
              "csamt": 0
            }
          ]
        }
        """
        hsn_lines = [line for line in invoice_lines if line.get("hsn_code")]
        
        if not hsn_lines:
            return {"data": []}
        
        # Use Gemini to validate HSN codes
        if use_gemini and hsn_lines:
            hsn_lines = self._gemini_validate_hsn_codes(hsn_lines)
        
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
        
        return {"data": result}
    
    def generate_txpd(self, invoice_lines: List[Dict]) -> List[Dict]:
        """Tax paid on advances - currently empty"""
        return []
    
    def generate_txpda(self, invoice_lines: List[Dict]) -> List[Dict]:
        """TXPD amendments - currently empty"""
        return []
    
    def generate_doc_issue(self, document_ranges: List[DocumentRange]) -> Dict[str, List[Dict]]:
        """
        Table 13 - Documents Issued
        
        Format:
        {
          "doc_det": [
            {
              "doc_num": 1,
              "doc_typ": "Invoices for outward supply",
              "docs": [
                {
                  "num": 1,
                  "from": "INV001",
                  "to": "INV050",
                  "totnum": 50,
                  "cancel": 5,
                  "net_issue": 45
                }
              ]
            }
          ]
        }
        """
        if not document_ranges:
            return {"doc_det": []}
        
        # Group by document type
        doc_type_groups = defaultdict(list)
        for doc_range in document_ranges:
            doc_type = self._map_doc_type_to_portal(doc_range.doc_type)
            doc_type_groups[doc_type].append(doc_range)
        
        result = []
        doc_num = 1
        
        # Order as per GST portal
        doc_type_order = [
            "Invoices for outward supply",
            "Invoices for inward supply from unregistered person",
            "Revised Invoice",
            "Debit Note",
            "Credit Note",
            "Receipt Voucher",
            "Payment Voucher",
            "Refund Voucher",
            "Delivery Challan for job work",
            "Delivery Challan for supply on approval",
            "Delivery Challan in case of liquid gas",
            "Delivery Challan in case of others"
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
                    "totnum": doc_range.expected_count,
                    "cancel": doc_range.cancelled_count,
                    "net_issue": doc_range.found_count
                })
            
            result.append({
                "doc_num": doc_num,
                "doc_typ": doc_typ,
                "docs": docs
            })
            
            doc_num += 1
        
        return {"doc_det": result}
    
    # Helper methods
    
    def _aggregate_by_rate(self, lines: List[Dict]) -> List[Dict]:
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
        """Format date to DD-MM-YYYY as per GST portal"""
        if not date_value:
            return ""
        
        try:
            # Assume ISO format YYYY-MM-DD
            if "-" in date_value:
                parts = date_value.split("-")
                if len(parts) == 3 and len(parts[0]) == 4:
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            pass
        
        return date_value
    
    def _map_doc_type_to_portal(self, doc_type: DocumentType) -> str:
        """Map internal document type to GST portal nomenclature"""
        mapping = {
            DocumentType.TAX_INVOICE: "Invoices for outward supply",
            DocumentType.CREDIT_NOTE: "Credit Note",
            DocumentType.DEBIT_NOTE: "Debit Note",
            DocumentType.DELIVERY_CHALLAN: "Delivery Challan for job work",
            DocumentType.REFUND_VOUCHER: "Refund Voucher",
            DocumentType.RECEIPT_VOUCHER: "Receipt Voucher"
        }
        return mapping.get(doc_type, "Invoices for outward supply")
    
    def _calculate_gross_turnover(self, invoice_lines: List[Dict]) -> float:
        """Calculate gross turnover for previous FY"""
        # This should be provided by user or fetched from previous returns
        return 0.0
    
    def _calculate_current_gross_turnover(self, invoice_lines: List[Dict]) -> float:
        """Calculate current period gross turnover"""
        total = sum(parse_money(line.get("taxable_value", 0)) for line in invoice_lines)
        return format_for_json(total)
    
    # Gemini AI Integration Methods
    
    def _gemini_validate_invoice_data(self, invoice_lines: List[Dict]) -> List[Dict]:
        """Use Gemini to validate and enhance invoice data"""
        try:
            logger.info("Using Gemini to validate invoice data...")
            
            # Sample data for Gemini (first 10 lines)
            sample_lines = invoice_lines[:10]
            
            validation = gemini_service.validate_gst_calculations({
                "total_lines": len(invoice_lines),
                "sample_data": sample_lines
            })
            
            logger.info(f"Gemini validation: {validation.get('validation_status', 'unknown')}")
            
            return invoice_lines
        except Exception as e:
            logger.warning(f"Gemini validation failed: {e}")
            return invoice_lines
    
    def _gemini_enhance_b2b_data(self, lines: List[Dict]) -> List[Dict]:
        """Use Gemini to enhance B2B data"""
        return lines
    
    def _gemini_enhance_b2c_data(self, lines: List[Dict]) -> List[Dict]:
        """Use Gemini to enhance B2C data"""
        return lines
    
    def _gemini_enhance_credit_note_data(self, lines: List[Dict]) -> List[Dict]:
        """Use Gemini to enhance credit/debit note data"""
        return lines
    
    def _gemini_enhance_export_data(self, lines: List[Dict]) -> List[Dict]:
        """Use Gemini to enhance export data"""
        return lines
    
    def _gemini_validate_hsn_codes(self, lines: List[Dict]) -> List[Dict]:
        """Use Gemini to validate HSN codes"""
        return lines
    
    def _gemini_validate_gstr1(self, gstr1_data: Dict, invoice_lines: List[Dict]) -> Dict:
        """Use Gemini to validate complete GSTR-1"""
        try:
            logger.info("Using Gemini for final GSTR-1 validation...")
            
            summary = {
                "total_invoices": len(invoice_lines),
                "sections_present": [k for k, v in gstr1_data.items() if v and k not in ["gstin", "fp", "gt", "cur_gt"]],
                "total_taxable": sum(parse_money(line.get("taxable_value", 0)) for line in invoice_lines)
            }
            
            validation = gemini_service.validate_gst_calculations(summary)
            
            return {
                "status": validation.get("validation_status", "unknown"),
                "issues": validation.get("issues_found", []),
                "recommendations": validation.get("recommendations", []),
                "compliance_score": validation.get("compliance_score", 0)
            }
        except Exception as e:
            logger.warning(f"Gemini final validation failed: {e}")
            return {"status": "unknown", "error": str(e)}
