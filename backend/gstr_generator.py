from typing import List, Dict
from decimal import Decimal, ROUND_HALF_UP
from models import (
    InvoiceLine,
    Table7Entry,
    Table13Entry,
    Table14Entry,
    GSTR1BOutput,
    GSTR3BOutput,
    GSTR3BSection31
)
from utils import group_by_state_and_rate, detect_invoice_ranges


class GSTRGenerator:
    """Generate GSTR-1B and GSTR-3B JSON outputs"""
    
    def __init__(self, gstin: str, filing_period: str, eco_gstin: str = "29AABCE1234F1Z5"):
        """
        Args:
            gstin: Seller's GSTIN
            filing_period: Filing period in MMYYYY format (e.g., "012025" for Jan 2025)
            eco_gstin: E-commerce operator GSTIN (Meesho)
        """
        self.gstin = gstin
        self.filing_period = filing_period
        self.eco_gstin = eco_gstin
    
    def generate_table7(self, invoice_lines: List[Dict]) -> List[Table7Entry]:
        """
        Generate Table 7 (B2C Others) - Unregistered buyers, invoice value <= 12.5L
        Group by state_code and gst_rate
        """
        # Filter only sales (exclude tax invoice entries)
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("state_code")
            and line.get("gst_rate") is not None
        ]
        
        if not sales_lines:
            return []
        
        # Group by state and rate
        grouped = group_by_state_and_rate(sales_lines)
        
        # Create Table 7 entries
        table7_entries = []
        for (state_code, gst_rate), data in grouped.items():
            entry = Table7Entry(
                pos=state_code,
                rate=gst_rate,
                txval=data["taxable_value"],
                iamt=data["igst_amount"],
                camt=data["cgst_amount"],
                samt=data["sgst_amount"]
            )
            table7_entries.append(entry)
        
        # Sort by state code and rate
        table7_entries.sort(key=lambda x: (x.pos, x.rate))
        
        return table7_entries
    
    def generate_table13(self, invoice_lines: List[Dict]) -> List[Table13Entry]:
        """
        Generate Table 13 (Documents Issued)
        Analyze invoice serial ranges
        """
        # Filter tax invoice entries
        invoice_entries = [
            line for line in invoice_lines
            if line.get("file_type") == "tax_invoice"
            and line.get("invoice_no")
        ]
        
        if not invoice_entries:
            return []
        
        # Extract invoice numbers
        invoice_numbers = [line["invoice_no"] for line in invoice_entries]
        
        # Detect ranges
        ranges = detect_invoice_ranges(invoice_numbers)
        
        # Create Table 13 entries
        table13_entries = []
        for range_data in ranges:
            entry = Table13Entry(
                doc_type="Invoices for outward supply",
                doc_num=range_data["found_count"],
                doc_from=range_data["doc_from"],
                doc_to=range_data["doc_to"],
                total_count=range_data["found_count"],
                cancelled=range_data["missing_count"]
            )
            table13_entries.append(entry)
        
        return table13_entries
    
    def generate_table14(self, invoice_lines: List[Dict]) -> List[Table14Entry]:
        """
        Generate Table 14 (Supplies through E-Commerce Operator)
        All Meesho sales are ECO supplies
        """
        # Filter sales lines only
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("taxable_value") is not None
        ]
        
        if not sales_lines:
            return []
        
        # Aggregate all ECO supplies
        total_taxable = Decimal("0")
        total_igst = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        
        for line in sales_lines:
            total_taxable += Decimal(str(line.get("taxable_value", 0)))
            total_igst += Decimal(str(line.get("igst_amount", 0)))
            total_cgst += Decimal(str(line.get("cgst_amount", 0)))
            total_sgst += Decimal(str(line.get("sgst_amount", 0)))
        
        # Round to 2 decimal places
        entry = Table14Entry(
            eco_gstin=self.eco_gstin,
            txval=float(total_taxable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            iamt=float(total_igst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            camt=float(total_cgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            samt=float(total_sgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        )
        
        return [entry]
    
    def generate_gstr1b(self, invoice_lines: List[Dict]) -> GSTR1BOutput:
        """Generate complete GSTR-1B JSON"""
        table7 = self.generate_table7(invoice_lines)
        table13 = self.generate_table13(invoice_lines)
        table14 = self.generate_table14(invoice_lines)
        
        gstr1b = GSTR1BOutput(
            gstin=self.gstin,
            fp=self.filing_period,
            table7=table7,
            table13=table13,
            table14=table14
        )
        
        return gstr1b
    
    def generate_gstr3b(self, invoice_lines: List[Dict]) -> GSTR3BOutput:
        """
        Generate GSTR-3B JSON (simplified)
        Section 3.1 - Outward taxable supplies (other than zero-rated, nil rated and exempted)
        """
        # Filter sales lines
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("taxable_value") is not None
        ]
        
        if not sales_lines:
            # Return zero values
            section_31 = GSTR3BSection31(txval=0.0)
            return GSTR3BOutput(
                gstin=self.gstin,
                fp=self.filing_period,
                section_31=section_31
            )
        
        # Aggregate totals
        total_taxable = Decimal("0")
        total_igst = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        
        for line in sales_lines:
            total_taxable += Decimal(str(line.get("taxable_value", 0)))
            total_igst += Decimal(str(line.get("igst_amount", 0)))
            total_cgst += Decimal(str(line.get("cgst_amount", 0)))
            total_sgst += Decimal(str(line.get("sgst_amount", 0)))
        
        # Round to 2 decimal places
        section_31 = GSTR3BSection31(
            txval=float(total_taxable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            iamt=float(total_igst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            camt=float(total_cgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            samt=float(total_sgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        )
        
        gstr3b = GSTR3BOutput(
            gstin=self.gstin,
            fp=self.filing_period,
            section_31=section_31
        )
        
        return gstr3b
    
    def validate_output(self, gstr1b: GSTR1BOutput, gstr3b: GSTR3BOutput) -> List[str]:
        """
        Validate and reconcile GSTR-1B and GSTR-3B outputs
        Returns list of validation warnings
        """
        warnings = []
        
        # Calculate GSTR-1B totals
        gstr1b_taxable = sum(entry.txval for entry in gstr1b.table7)
        gstr1b_igst = sum(entry.iamt for entry in gstr1b.table7)
        gstr1b_cgst = sum(entry.camt for entry in gstr1b.table7)
        gstr1b_sgst = sum(entry.samt for entry in gstr1b.table7)
        
        # Compare with GSTR-3B
        gstr3b_taxable = gstr3b.section_31.txval
        gstr3b_igst = gstr3b.section_31.iamt
        gstr3b_cgst = gstr3b.section_31.camt
        gstr3b_sgst = gstr3b.section_31.samt
        
        # Check differences (allow 0.01 tolerance for rounding)
        tolerance = 0.02
        
        if abs(gstr1b_taxable - gstr3b_taxable) > tolerance:
            warnings.append(
                f"Taxable value mismatch: GSTR-1B Table 7 = {gstr1b_taxable:.2f}, "
                f"GSTR-3B = {gstr3b_taxable:.2f}"
            )
        
        if abs(gstr1b_igst - gstr3b_igst) > tolerance:
            warnings.append(
                f"IGST mismatch: GSTR-1B Table 7 = {gstr1b_igst:.2f}, "
                f"GSTR-3B = {gstr3b_igst:.2f}"
            )
        
        if abs(gstr1b_cgst - gstr3b_cgst) > tolerance:
            warnings.append(
                f"CGST mismatch: GSTR-1B Table 7 = {gstr1b_cgst:.2f}, "
                f"GSTR-3B = {gstr3b_cgst:.2f}"
            )
        
        if abs(gstr1b_sgst - gstr3b_sgst) > tolerance:
            warnings.append(
                f"SGST mismatch: GSTR-1B Table 7 = {gstr1b_sgst:.2f}, "
                f"GSTR-3B = {gstr3b_sgst:.2f}"
            )
        
        # Check for empty tables
        if not gstr1b.table7:
            warnings.append("Table 7 (B2C Others) is empty")
        
        if not gstr1b.table13:
            warnings.append("Table 13 (Documents Issued) is empty - no invoice serial data found")
        
        if not gstr1b.table14:
            warnings.append("Table 14 (ECO Supplies) is empty")
        
        return warnings
