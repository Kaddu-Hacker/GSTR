from typing import List, Dict
from decimal import Decimal, ROUND_HALF_UP
from models import (
    InvoiceLine,
    Table7Entry,
    Table13Entry,
    Table14Entry,
    GSTR1BOutput,
    GSTR3BOutput,
    GSTR3BSection31a,
    GSTR3BSection311,
    GSTR3BSection32
)
from utils import group_by_state_and_rate, detect_invoice_ranges


class GSTRGenerator:
    """Generate GSTR-1B and GSTR-3B JSON outputs"""
    
    def __init__(self, gstin: str, filing_period: str, eco_gstin: str = "07AARCM9332R1CQ"):
        """
        Args:
            gstin: Seller's GSTIN
            filing_period: Filing period in MMYYYY format (e.g., "012025" for Jan 2025)
            eco_gstin: E-commerce operator GSTIN (Meesho: 07AARCM9332R1CQ)
        """
        self.gstin = gstin
        self.filing_period = filing_period
        self.eco_gstin = eco_gstin
    
    def generate_table7(self, invoice_lines: List[Dict]) -> List[Table7Entry]:
        """
        Generate Table 7 (B2C Others) - Unregistered buyers, invoice value <= 12.5L
        Group by state_code and gst_rate
        
        IMPORTANT: ECO supplies should be reported in Table 14, not Table 7.
        However, per IRIS GST guidance, ECO supplies that appear in Table 14
        are ALSO included in Table 7 as normal B2C supplies.
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
        Analyze invoice serial ranges grouped by document type
        
        Includes:
        - Invoices for outward supply
        - Credit Notes (returns)
        - Debit Notes
        - Delivery Challans (if any)
        """
        # Filter tax invoice entries
        invoice_entries = [
            line for line in invoice_lines
            if line.get("file_type") == "tax_invoice"
            and line.get("invoice_no")
        ]
        
        if not invoice_entries:
            return []
        
        # Group by invoice_type if available
        type_groups = {}
        for line in invoice_entries:
            doc_type = line.get("invoice_type", "Invoice")
            if doc_type not in type_groups:
                type_groups[doc_type] = []
            type_groups[doc_type].append(line["invoice_no"])
        
        # Create Table 13 entries for each document type
        table13_entries = []
        
        for doc_type, invoice_numbers in type_groups.items():
            # Detect ranges for this type
            ranges = detect_invoice_ranges(invoice_numbers)
            
            for range_data in ranges:
                # Map document type to GST standard nomenclature
                if "credit" in doc_type.lower():
                    gst_doc_type = "Credit Notes"
                elif "debit" in doc_type.lower():
                    gst_doc_type = "Debit Notes"
                elif "challan" in doc_type.lower() or "delivery" in doc_type.lower():
                    gst_doc_type = "Delivery Challans"
                else:
                    gst_doc_type = "Invoices for outward supply"
                
                entry = Table13Entry(
                    doc_type=gst_doc_type,
                    doc_num=range_data["found_count"],
                    doc_from=range_data["doc_from"],
                    doc_to=range_data["doc_to"],
                    total_count=range_data["found_count"],
                    cancelled=range_data["missing_count"]
                )
                table13_entries.append(entry)
        
        # Sort by document type for consistency
        sort_order = {
            "Invoices for outward supply": 1,
            "Credit Notes": 2,
            "Debit Notes": 3,
            "Delivery Challans": 4
        }
        table13_entries.sort(key=lambda x: (sort_order.get(x.doc_type, 99), x.doc_from))
        
        return table13_entries
    
    def generate_table14(self, invoice_lines: List[Dict]) -> List[Table14Entry]:
        """
        Generate Table 14 (Supplies through E-Commerce Operator)
        All Meesho sales are ECO supplies with TCS collected by ECO
        
        Table 14(a): Supplies through ECO where ECO collects TCS
        Table 14(b): Supplies where ECO is liable to pay tax u/s 9(5) (rare for goods)
        
        For most Meesho sellers, all supplies go to 14(a) as Meesho collects TCS.
        """
        # Filter sales lines only
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("taxable_value") is not None
        ]
        
        if not sales_lines:
            return []
        
        # Aggregate all ECO supplies (14(a) - ECO collects TCS)
        total_taxable = Decimal("0")
        total_igst = Decimal("0")
        total_cgst = Decimal("0")
        total_sgst = Decimal("0")
        
        for line in sales_lines:
            total_taxable += Decimal(str(line.get("taxable_value") or 0))
            total_igst += Decimal(str(line.get("igst_amount") or 0))
            total_cgst += Decimal(str(line.get("cgst_amount") or 0))
            total_sgst += Decimal(str(line.get("sgst_amount") or 0))
        
        # Round to 2 decimal places
        entry = Table14Entry(
            eco_gstin=self.eco_gstin,  # Meesho GSTIN: 07AARCM9332R1CQ
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
        Generate GSTR-3B JSON with proper section mapping
        
        Section 3.1(a): Outward taxable supplies (other than zero-rated, nil-rated, exempted)
                        - Normal B2C supplies (non-ECO)
        
        Section 3.1.1(ii): Supplies made through ECO where supplier reports
                           - All Meesho sales go here as ECO collects TCS
        
        Section 3.2: Inter-state supplies to unregistered persons
                     - Subset of 3.1(a) that are inter-state
        """
        # Filter sales lines
        sales_lines = [
            line for line in invoice_lines
            if line.get("file_type") in ["tcs_sales", "tcs_sales_return"]
            and line.get("taxable_value") is not None
        ]
        
        if not sales_lines:
            # Return zero values
            section_31a = GSTR3BSection31a(txval=0.0)
            section_311 = GSTR3BSection311(txval=0.0)
            section_32 = GSTR3BSection32(txval=0.0)
            
            return GSTR3BOutput(
                gstin=self.gstin,
                fp=self.filing_period,
                section_31a=section_31a,
                section_311=section_311,
                section_32=section_32
            )
        
        # Since ALL sales are through Meesho (ECO), they ALL go to Section 3.1.1(ii)
        # Section 3.1(a) would be for non-ECO sales (none in this case)
        
        # Aggregate totals for ECO supplies (Section 3.1.1(ii))
        eco_taxable = Decimal("0")
        eco_igst = Decimal("0")
        eco_cgst = Decimal("0")
        eco_sgst = Decimal("0")
        
        # Aggregate inter-state supplies (Section 3.2)
        interstate_taxable = Decimal("0")
        interstate_igst = Decimal("0")
        
        for line in sales_lines:
            taxable = Decimal(str(line.get("taxable_value", 0)))
            igst = Decimal(str(line.get("igst_amount", 0)))
            cgst = Decimal(str(line.get("cgst_amount", 0)))
            sgst = Decimal(str(line.get("sgst_amount", 0)))
            
            # All go to ECO section
            eco_taxable += taxable
            eco_igst += igst
            eco_cgst += cgst
            eco_sgst += sgst
            
            # If inter-state (IGST > 0), also count in Section 3.2
            if line.get("is_intra_state") == False:
                interstate_taxable += taxable
                interstate_igst += igst
        
        # Round to 2 decimal places
        # Section 3.1(a) - No non-ECO sales in this case
        section_31a = GSTR3BSection31a(
            txval=0.0,
            iamt=0.0,
            camt=0.0,
            samt=0.0
        )
        
        # Section 3.1.1(ii) - All ECO supplies
        section_311 = GSTR3BSection311(
            txval=float(eco_taxable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            iamt=float(eco_igst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            camt=float(eco_cgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            samt=float(eco_sgst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        )
        
        # Section 3.2 - Inter-state to unregistered
        section_32 = GSTR3BSection32(
            txval=float(interstate_taxable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            iamt=float(interstate_igst.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        )
        
        gstr3b = GSTR3BOutput(
            gstin=self.gstin,
            fp=self.filing_period,
            section_31a=section_31a,
            section_311=section_311,
            section_32=section_32
        )
        
        return gstr3b
    
    def validate_output(self, gstr1b: GSTR1BOutput, gstr3b: GSTR3BOutput) -> List[str]:
        """
        Validate and reconcile GSTR-1B and GSTR-3B outputs
        Returns list of validation warnings
        """
        warnings = []
        
        # Calculate GSTR-1B totals (Table 7)
        gstr1b_table7_taxable = sum(entry.txval for entry in gstr1b.table7)
        gstr1b_table7_igst = sum(entry.iamt for entry in gstr1b.table7)
        gstr1b_table7_cgst = sum(entry.camt for entry in gstr1b.table7)
        gstr1b_table7_sgst = sum(entry.samt for entry in gstr1b.table7)
        
        # Calculate GSTR-1B Table 14 totals (ECO supplies)
        gstr1b_table14_taxable = sum(entry.txval for entry in gstr1b.table14)
        gstr1b_table14_igst = sum(entry.iamt for entry in gstr1b.table14)
        gstr1b_table14_cgst = sum(entry.camt for entry in gstr1b.table14)
        gstr1b_table14_sgst = sum(entry.samt for entry in gstr1b.table14)
        
        # Compare Table 14 with GSTR-3B Section 3.1.1(ii) - should match
        gstr3b_eco_taxable = gstr3b.section_311.txval
        gstr3b_eco_igst = gstr3b.section_311.iamt
        gstr3b_eco_cgst = gstr3b.section_311.camt
        gstr3b_eco_sgst = gstr3b.section_311.samt
        
        # Check differences (allow 0.02 tolerance for rounding)
        tolerance = 0.02
        
        # Validate Table 14 matches Section 3.1.1(ii)
        if abs(gstr1b_table14_taxable - gstr3b_eco_taxable) > tolerance:
            warnings.append(
                f"ECO supplies mismatch: GSTR-1B Table 14 = ₹{gstr1b_table14_taxable:.2f}, "
                f"GSTR-3B Section 3.1.1(ii) = ₹{gstr3b_eco_taxable:.2f}"
            )
        
        if abs(gstr1b_table14_igst - gstr3b_eco_igst) > tolerance:
            warnings.append(
                f"ECO IGST mismatch: Table 14 = ₹{gstr1b_table14_igst:.2f}, "
                f"Section 3.1.1(ii) = ₹{gstr3b_eco_igst:.2f}"
            )
        
        if abs(gstr1b_table14_cgst - gstr3b_eco_cgst) > tolerance:
            warnings.append(
                f"ECO CGST mismatch: Table 14 = ₹{gstr1b_table14_cgst:.2f}, "
                f"Section 3.1.1(ii) = ₹{gstr3b_eco_cgst:.2f}"
            )
        
        if abs(gstr1b_table14_sgst - gstr3b_eco_sgst) > tolerance:
            warnings.append(
                f"ECO SGST mismatch: Table 14 = ₹{gstr1b_table14_sgst:.2f}, "
                f"Section 3.1.1(ii) = ₹{gstr3b_eco_sgst:.2f}"
            )
        
        # Validate Table 7 matches Table 14 (per IRIS GST, ECO supplies appear in both)
        if abs(gstr1b_table7_taxable - gstr1b_table14_taxable) > tolerance:
            warnings.append(
                f"Note: Table 7 (₹{gstr1b_table7_taxable:.2f}) and Table 14 (₹{gstr1b_table14_taxable:.2f}) "
                f"should match as ECO supplies are reported in both tables"
            )
        
        # Check for empty tables
        if not gstr1b.table7:
            warnings.append("Table 7 (B2C Others) is empty")
        
        if not gstr1b.table13:
            warnings.append("Table 13 (Documents Issued) is empty - no invoice serial data found")
        
        if not gstr1b.table14:
            warnings.append("Table 14 (ECO Supplies) is empty")
        
        # Check Section 3.2 is subset of inter-state supplies
        if gstr3b.section_32.txval > gstr3b_eco_taxable + tolerance:
            warnings.append(
                f"Section 3.2 inter-state (₹{gstr3b.section_32.txval:.2f}) exceeds "
                f"total ECO supplies (₹{gstr3b_eco_taxable:.2f})"
            )
        
        return warnings
