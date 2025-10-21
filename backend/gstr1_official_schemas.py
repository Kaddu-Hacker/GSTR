"""
Official GSTR-1 JSON Schemas - Complete and Portal-Compliant
Based on GST Portal specifications and offline tool format (2024-2025)

This module defines the exact JSON structure for ALL GSTR-1 tables:
- B2B, B2CL, B2CS, CDNR, CDNUR, EXP, EXPWP, AT, ATADJ, HSN, DOC_ISS, EXEMP (NIL)
- All amendments: B2BA, B2CLA, B2CSA, CDNRA, CDNURA, EXPA, ATADJA

Field naming conventions follow GST portal exactly:
- ctin: Customer GSTIN
- inv: Invoice array
- inum: Invoice number
- idt: Invoice date (DD-MM-YYYY)
- val: Invoice value
- pos: Place of supply (state code)
- rchrg: Reverse charge (Y/N)
- inv_typ: Invoice type (R=Regular, SEWP=SEZ with payment, SEWOP=SEZ without payment, DE=Deemed Export, CBW=Export with payment, EXPWOP=Export without payment)
- itms: Items array
- num: Item number
- itm_det: Item details
- txval: Taxable value
- rt: GST rate
- iamt: IGST amount
- camt: CGST amount
- samt: SGST amount
- csamt: Cess amount
"""

from typing import List, Dict, Optional, Any
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GSTR1OfficialSchemas:
    """
    Complete official GSTR-1 schemas matching GST portal format
    All tables with exact field names and structure
    """
    
    @staticmethod
    def format_date(date_obj: Any) -> str:
        """Convert date to DD-MM-YYYY format (GST portal standard)"""
        if isinstance(date_obj, str):
            # Try to parse and reformat
            try:
                if '-' in date_obj:
                    parts = date_obj.split('-')
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        return f"{parts[2]}-{parts[1]}-{parts[0]}"
                    else:  # DD-MM-YYYY
                        return date_obj
                return date_obj
            except:
                return date_obj
        elif isinstance(date_obj, datetime):
            return date_obj.strftime("%d-%m-%Y")
        return str(date_obj)
    
    @staticmethod
    def format_decimal(value: Any, precision: int = 2) -> float:
        """Format decimal values with proper precision"""
        try:
            if isinstance(value, Decimal):
                return float(round(value, precision))
            return round(float(value or 0), precision)
        except:
            return 0.0
    
    # ============================================================================
    # B2B - TABLE 4: Invoices for Registered Buyers
    # ============================================================================
    
    @staticmethod
    def b2b_invoice_schema(
        ctin: str,
        invoices: List[Dict]
    ) -> Dict:
        """
        B2B Invoice Schema - Table 4
        
        Args:
            ctin: Customer GSTIN (15 chars)
            invoices: List of invoice dictionaries
        
        Returns:
            Official B2B invoice structure
        """
        return {
            "ctin": ctin,  # Customer GSTIN
            "inv": invoices
        }
    
    @staticmethod
    def b2b_invoice_item(
        inum: str,
        idt: str,
        val: float,
        pos: str,
        rchrg: str,
        inv_typ: str,
        items: List[Dict]
    ) -> Dict:
        """
        B2B Invoice Item
        
        Args:
            inum: Invoice number (max 16 chars)
            idt: Invoice date (DD-MM-YYYY)
            val: Invoice value (including tax)
            pos: Place of supply (2-digit state code)
            rchrg: Reverse charge (Y/N)
            inv_typ: Invoice type (R/SEWP/SEWOP/DE/CBW)
            items: List of item details
        """
        return {
            "inum": inum,
            "idt": idt,
            "val": val,
            "pos": pos,
            "rchrg": rchrg,
            "inv_typ": inv_typ,
            "itms": items
        }
    
    @staticmethod
    def b2b_item_detail(
        num: int,
        txval: float,
        rt: float,
        iamt: float = 0.0,
        camt: float = 0.0,
        samt: float = 0.0,
        csamt: float = 0.0
    ) -> Dict:
        """
        B2B Item Detail
        
        Args:
            num: Item serial number
            txval: Taxable value
            rt: Tax rate (%)
            iamt: IGST amount
            camt: CGST amount
            samt: SGST amount
            csamt: Cess amount
        """
        return {
            "num": num,
            "itm_det": {
                "txval": txval,
                "rt": rt,
                "iamt": iamt,
                "camt": camt,
                "samt": samt,
                "csamt": csamt
            }
        }
    
    # ============================================================================
    # B2CL - TABLE 5: Large Invoices (> 2.5L) for Unregistered Buyers
    # ============================================================================
    
    @staticmethod
    def b2cl_invoice_schema(
        pos: str,
        invoices: List[Dict]
    ) -> Dict:
        """
        B2CL Invoice Schema - Table 5
        For unregistered buyers, invoice value > 2.5 lakh
        
        Args:
            pos: Place of supply (state code)
            invoices: List of invoice dictionaries
        """
        return {
            "pos": pos,
            "inv": invoices
        }
    
    @staticmethod
    def b2cl_invoice_item(
        inum: str,
        idt: str,
        val: float,
        etin: Optional[str] = None,
        items: List[Dict] = None
    ) -> Dict:
        """
        B2CL Invoice Item
        
        Args:
            inum: Invoice number
            idt: Invoice date (DD-MM-YYYY)
            val: Invoice value
            etin: E-way bill transporter ID (optional)
            items: List of item details
        """
        invoice = {
            "inum": inum,
            "idt": idt,
            "val": val,
            "itms": items or []
        }
        if etin:
            invoice["etin"] = etin
        return invoice
    
    # ============================================================================
    # B2CS - TABLE 7: Small Invoices (<= 2.5L) for Unregistered Buyers
    # ============================================================================
    
    @staticmethod
    def b2cs_entry_schema(
        sply_ty: str,
        pos: str,
        typ: str,
        txval: float,
        rt: float,
        iamt: float = 0.0,
        camt: float = 0.0,
        samt: float = 0.0,
        csamt: float = 0.0
    ) -> Dict:
        """
        B2CS Entry Schema - Table 7
        Summary of small invoices grouped by supply type, place, and rate
        
        Args:
            sply_ty: Supply type (INTRA for intra-state, INTER for inter-state)
            pos: Place of supply (state code)
            typ: Type (OE=Outward taxable, EXPWP=Export with payment, EXPWOP=Export without payment)
            txval: Taxable value (sum)
            rt: Tax rate
            iamt: IGST amount (for inter-state)
            camt: CGST amount (for intra-state)
            samt: SGST amount (for intra-state)
            csamt: Cess amount
        """
        return {
            "sply_ty": sply_ty,
            "pos": pos,
            "typ": typ,
            "txval": txval,
            "rt": rt,
            "iamt": iamt,
            "camt": camt,
            "samt": samt,
            "csamt": csamt
        }
    
    # ============================================================================
    # CDNR - TABLE 9A: Credit/Debit Notes for Registered Customers
    # ============================================================================
    
    @staticmethod
    def cdnr_note_schema(
        ctin: str,
        notes: List[Dict]
    ) -> Dict:
        """
        CDNR Note Schema - Table 9A
        Credit/Debit notes to registered customers
        
        Args:
            ctin: Customer GSTIN
            notes: List of note dictionaries
        """
        return {
            "ctin": ctin,
            "nt": notes
        }
    
    @staticmethod
    def cdnr_note_item(
        ntty: str,
        nt_num: str,
        nt_dt: str,
        val: float,
        pos: str,
        rchrg: str,
        inv_typ: str,
        items: List[Dict]
    ) -> Dict:
        """
        CDNR Note Item
        
        Args:
            ntty: Note type (C=Credit, D=Debit)
            nt_num: Note number
            nt_dt: Note date (DD-MM-YYYY)
            val: Note value
            pos: Place of supply
            rchrg: Reverse charge (Y/N)
            inv_typ: Invoice type
            items: List of item details
        """
        return {
            "ntty": ntty,
            "nt_num": nt_num,
            "nt_dt": nt_dt,
            "val": val,
            "pos": pos,
            "rchrg": rchrg,
            "inv_typ": inv_typ,
            "itms": items
        }
    
    # ============================================================================
    # CDNUR - TABLE 9B: Credit/Debit Notes for Unregistered Customers
    # ============================================================================
    
    @staticmethod
    def cdnur_note_schema(
        ntty: str,
        nt_num: str,
        nt_dt: str,
        val: float,
        pos: str,
        typ: str,
        items: List[Dict]
    ) -> Dict:
        """
        CDNUR Note Schema - Table 9B
        Credit/Debit notes to unregistered customers
        
        Args:
            ntty: Note type (C/D)
            nt_num: Note number
            nt_dt: Note date
            val: Note value
            pos: Place of supply
            typ: Type (B2CL/EXPWP/EXPWOP)
            items: Item details
        """
        return {
            "ntty": ntty,
            "nt_num": nt_num,
            "nt_dt": nt_dt,
            "val": val,
            "pos": pos,
            "typ": typ,
            "itms": items
        }
    
    # ============================================================================
    # EXP - TABLE 6A: Export Invoices
    # ============================================================================
    
    @staticmethod
    def exp_invoice_schema(
        exp_typ: str,
        invoices: List[Dict]
    ) -> Dict:
        """
        Export Invoice Schema - Table 6A
        
        Args:
            exp_typ: Export type (WPAY=With payment, WOPAY=Without payment)
            invoices: List of export invoices
        """
        return {
            "exp_typ": exp_typ,
            "inv": invoices
        }
    
    @staticmethod
    def exp_invoice_item(
        inum: str,
        idt: str,
        val: float,
        sbpcode: str,
        sbnum: Optional[str] = None,
        sbdt: Optional[str] = None,
        items: List[Dict] = None
    ) -> Dict:
        """
        Export Invoice Item
        
        Args:
            inum: Invoice number
            idt: Invoice date
            val: Invoice value
            sbpcode: Shipping bill port code (6 digits)
            sbnum: Shipping bill number (optional)
            sbdt: Shipping bill date (optional, DD-MM-YYYY)
            items: Item details
        """
        invoice = {
            "inum": inum,
            "idt": idt,
            "val": val,
            "sbpcode": sbpcode,
            "itms": items or []
        }
        if sbnum:
            invoice["sbnum"] = sbnum
        if sbdt:
            invoice["sbdt"] = sbdt
        return invoice
    
    # ============================================================================
    # AT - TABLE 11A: Tax on Advances Received
    # ============================================================================
    
    @staticmethod
    def at_entry_schema(
        pos: str,
        sply_ty: str,
        ad_amt: float,
        rt: float,
        iamt: float = 0.0,
        camt: float = 0.0,
        samt: float = 0.0,
        csamt: float = 0.0
    ) -> Dict:
        """
        Advance Tax Entry - Table 11A
        Tax on advances received (before invoice)
        
        Args:
            pos: Place of supply
            sply_ty: Supply type (INTRA/INTER)
            ad_amt: Advance amount
            rt: Tax rate
            iamt: IGST amount
            camt: CGST amount
            samt: SGST amount
            csamt: Cess amount
        """
        return {
            "pos": pos,
            "sply_ty": sply_ty,
            "ad_amt": ad_amt,
            "rt": rt,
            "iamt": iamt,
            "camt": camt,
            "samt": samt,
            "csamt": csamt
        }
    
    # ============================================================================
    # ATADJ - TABLE 11B: Adjustment of Advances
    # ============================================================================
    
    @staticmethod
    def atadj_entry_schema(
        pos: str,
        sply_ty: str,
        ad_amt: float,
        rt: float,
        iamt: float = 0.0,
        camt: float = 0.0,
        samt: float = 0.0,
        csamt: float = 0.0
    ) -> Dict:
        """
        Advance Adjustment Entry - Table 11B
        Adjustment of tax on advances against invoices
        
        Args:
            pos: Place of supply
            sply_ty: Supply type
            ad_amt: Advance amount adjusted
            rt: Tax rate
            iamt: IGST amount
            camt: CGST amount
            samt: SGST amount
            csamt: Cess amount
        """
        return {
            "pos": pos,
            "sply_ty": sply_ty,
            "ad_amt": ad_amt,
            "rt": rt,
            "iamt": iamt,
            "camt": camt,
            "samt": samt,
            "csamt": csamt
        }
    
    # ============================================================================
    # HSN - TABLE 12: HSN/SAC Summary (MANDATORY from 2025)
    # ============================================================================
    
    @staticmethod
    def hsn_entry_schema(
        hsn_sc: str,
        desc: str,
        uqc: str,
        qty: float,
        val: float,
        txval: float,
        rt: float,
        iamt: float = 0.0,
        camt: float = 0.0,
        samt: float = 0.0,
        csamt: float = 0.0
    ) -> Dict:
        """
        HSN Summary Entry - Table 12 (MANDATORY)
        Rate-wise summary of outward supplies
        
        Args:
            hsn_sc: HSN/SAC code (4/6/8 digits based on turnover)
            desc: Description of goods/services
            uqc: Unit Quantity Code (e.g., KGS, PCS, NOS)
            qty: Total quantity
            val: Total value (including tax)
            txval: Taxable value
            rt: Tax rate
            iamt: IGST amount
            camt: CGST amount
            samt: SGST amount
            csamt: Cess amount
        """
        return {
            "num": 1,  # Serial number
            "hsn_sc": hsn_sc,
            "desc": desc,
            "uqc": uqc,
            "qty": qty,
            "val": val,
            "txval": txval,
            "rt": rt,
            "iamt": iamt,
            "camt": camt,
            "samt": samt,
            "csamt": csamt
        }
    
    # ============================================================================
    # DOC_ISS - TABLE 13: Documents Issued (MANDATORY from May 2025)
    # ============================================================================
    
    @staticmethod
    def doc_iss_entry_schema(
        doc_num: int,
        docs: List[Dict]
    ) -> Dict:
        """
        Document Issued Entry - Table 13 (MANDATORY)
        Summary of all documents issued during tax period
        
        Args:
            doc_num: Document serial number
            docs: List of document details
        """
        return {
            "doc_num": doc_num,
            "docs": docs
        }
    
    @staticmethod
    def doc_iss_detail(
        num: int,
        from_sr: str,
        to_sr: str,
        totnum: int,
        cancel: int = 0,
        net_issue: int = None
    ) -> Dict:
        """
        Document Detail
        
        Args:
            num: Serial number
            from_sr: Starting serial number
            to_sr: Ending serial number
            totnum: Total number of documents
            cancel: Cancelled documents
            net_issue: Net issued (totnum - cancel)
        """
        if net_issue is None:
            net_issue = totnum - cancel
        
        return {
            "num": num,
            "from": from_sr,
            "to": to_sr,
            "totnum": totnum,
            "cancel": cancel,
            "net_issue": net_issue
        }
    
    # ============================================================================
    # EXEMP (NIL) - TABLE 8: Nil Rated, Exempted and Non-GST Supplies
    # ============================================================================
    
    @staticmethod
    def exemp_entry_schema(
        sply_ty: str,
        nil_amt: float = 0.0,
        expt_amt: float = 0.0,
        ngsup_amt: float = 0.0
    ) -> Dict:
        """
        Exempted Supplies Entry - Table 8
        Nil rated, exempted and non-GST outward supplies
        
        Args:
            sply_ty: Supply type (INTRB2B/INTRB2C/INTERB2B/INTERB2C)
            nil_amt: Nil rated supplies amount
            expt_amt: Exempted supplies amount
            ngsup_amt: Non-GST supplies amount
        """
        return {
            "sply_ty": sply_ty,
            "nil_amt": nil_amt,
            "expt_amt": expt_amt,
            "ngsup_amt": ngsup_amt
        }
    
    # ============================================================================
    # Complete GSTR-1 Return Structure
    # ============================================================================
    
    @staticmethod
    def complete_gstr1_structure(
        gstin: str,
        fp: str,
        gt: float = 0.0,
        cur_gt: float = 0.0
    ) -> Dict:
        """
        Complete GSTR-1 Return Structure
        
        Args:
            gstin: Taxpayer GSTIN
            fp: Filing period (MMYYYY, e.g., 012025)
            gt: Gross turnover of the taxpayer in the previous financial year
            cur_gt: Gross turnover of the taxpayer up to the month in current financial year
        
        Returns:
            Empty GSTR-1 structure with all tables
        """
        return {
            "gstin": gstin,
            "fp": fp,
            "gt": gt,
            "cur_gt": cur_gt,
            "b2b": [],
            "b2cl": [],
            "b2cs": [],
            "cdnr": [],
            "cdnur": [],
            "exp": [],
            "at": [],
            "atadj": [],
            "hsn": [],
            "doc_iss": [],
            "exemp": [],
            # Amendments
            "b2ba": [],
            "b2cla": [],
            "b2csa": [],
            "cdnra": [],
            "cdnura": [],
            "expa": [],
            "atadja": []
        }


# Validation rules and constants
VALIDATION_RULES = {
    "gstin_length": 15,
    "state_code_length": 2,
    "invoice_num_max_length": 16,
    "date_format": "DD-MM-YYYY",
    "b2cl_threshold": 250000,  # 2.5 lakh
    "reverse_charge_values": ["Y", "N"],
    "supply_types": ["INTRA", "INTER"],
    "invoice_types": {
        "R": "Regular",
        "SEWP": "SEZ with payment",
        "SEWOP": "SEZ without payment",
        "DE": "Deemed Export",
        "CBW": "Export with payment"
    },
    "note_types": {"C": "Credit Note", "D": "Debit Note"},
    "export_types": {"WPAY": "With Payment", "WOPAY": "Without Payment"},
    "hsn_digits_by_turnover": {
        "below_1.5cr": 0,  # Not mandatory
        "1.5cr_to_5cr": 2,
        "5cr_to_10cr": 4,
        "above_10cr": 6
    },
    "mandatory_tables": ["b2b", "b2cl", "b2cs", "hsn", "doc_iss"],  # From 2025
    "uqc_codes": ["BAG", "BAL", "BDL", "BKL", "BOU", "BOX", "BTL", "BUN", "CAN", "CBM", "CCM", "CMS", "CTN", "DOZ", "DRM", "GGK", "GMS", "GRS", "GYD", "KGS", "KLR", "KME", "LTR", "MLT", "MTR", "MTS", "NOS", "OTH", "PAC", "PCS", "PRS", "QTL", "ROL", "SET", "SQF", "SQM", "SQY", "TBS", "TGM", "THD", "TON", "TUB", "UGS", "UNT", "YDS"]
}
