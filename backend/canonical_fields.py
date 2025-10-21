"""Canonical field mappings and synonyms for GSTR-1 sections"""

from typing import Dict, List

# Canonical field synonyms for auto-mapping
CANONICAL_FIELDS = {
    # Common fields across sections
    "gstin_uin": [
        "gstin of recipient", "recipient gstin", "bill to gstin", "buyer gstin",
        "ctin", "gstin/uin", "gstin", "uin"
    ],
    "invoice_no": [
        "invoice number", "invoice no.", "inv no", "invoice no", "inv_no",
        "bill no", "bill number"
    ],
    "invoice_date": [
        "invoice date", "date", "inv date", "bill date", "transaction date"
    ],
    "taxable_value": [
        "taxable value", "total_taxable_sale_value", "txval", "taxable val",
        "assessable value", "value", "invoice value"
    ],
    "place_of_supply": [
        "place of supply", "pos", "state", "end_customer_state_new",
        "customer state", "supply state", "destination state"
    ],
    "gst_rate": [
        "gst rate", "gst_rate", "rate", "tax rate", "gst %", "rate %"
    ],
    "cgst_amount": [
        "cgst", "cgst amount", "camt", "central gst"
    ],
    "sgst_amount": [
        "sgst", "sgst amount", "samt", "state gst"
    ],
    "igst_amount": [
        "igst", "igst amount", "iamt", "integrated gst"
    ],
    "cess_amount": [
        "cess", "cess amount", "csamt"
    ],
    
    # B2B specific
    "reverse_charge": [
        "reverse charge", "rcm", "is reverse charge", "rev charge"
    ],
    "invoice_type": [
        "invoice type", "type", "doc type", "document type"
    ],
    
    # HSN specific
    "hsn_code": [
        "hsn", "hsn code", "hsn_sc", "sac", "sac code"
    ],
    "description": [
        "description", "desc", "item description", "goods description"
    ],
    "uqc": [
        "uqc", "unit", "unit of measurement", "uom"
    ],
    "quantity": [
        "quantity", "qty", "total quantity"
    ],
    
    # Credit/Debit notes
    "note_number": [
        "note number", "note no", "credit note no", "debit note no",
        "cn no", "dn no"
    ],
    "note_date": [
        "note date", "cn date", "dn date"
    ],
    "note_type": [
        "note type", "document type", "type"
    ],
    
    # Export specific
    "shipping_bill_no": [
        "shipping bill no", "shipping bill number", "sb no"
    ],
    "shipping_bill_date": [
        "shipping bill date", "sb date"
    ],
    "port_code": [
        "port code", "port"
    ]
}

# Document type mapping to canonical names
DOCUMENT_TYPES = {
    "invoice": "tax_invoice",
    "tax invoice": "tax_invoice",
    "credit note": "credit_note",
    "credit": "credit_note",
    "cn": "credit_note",
    "debit note": "debit_note",
    "debit": "debit_note",
    "dn": "debit_note",
    "delivery challan": "delivery_challan",
    "challan": "delivery_challan",
    "refund voucher": "refund_voucher",
    "refund": "refund_voucher",
    "receipt voucher": "receipt_voucher",
    "receipt": "receipt_voucher"
}

# GSTR-1 section detection rules
SECTION_RULES = {
    "b2b": {
        "description": "B2B - Registered buyers",
        "required_fields": ["gstin_uin", "invoice_no", "taxable_value"],
        "conditions": lambda row: row.get("gstin_uin") and len(str(row.get("gstin_uin", "")).strip()) == 15
    },
    "b2cl": {
        "description": "B2C Large - Unregistered buyers with invoice value > 2.5L",
        "required_fields": ["invoice_no", "taxable_value", "place_of_supply"],
        "conditions": lambda row: not row.get("gstin_uin") and row.get("taxable_value", 0) > 250000
    },
    "b2cs": {
        "description": "B2C Small - Unregistered buyers with invoice value <= 2.5L",
        "required_fields": ["taxable_value", "place_of_supply", "gst_rate"],
        "conditions": lambda row: not row.get("gstin_uin") and row.get("taxable_value", 0) <= 250000
    },
    "cdnr": {
        "description": "Credit/Debit Notes - Registered",
        "required_fields": ["gstin_uin", "note_number", "taxable_value"],
        "conditions": lambda row: row.get("gstin_uin") and row.get("note_type") in ["credit_note", "debit_note"]
    },
    "cdnur": {
        "description": "Credit/Debit Notes - Unregistered",
        "required_fields": ["note_number", "taxable_value"],
        "conditions": lambda row: not row.get("gstin_uin") and row.get("note_type") in ["credit_note", "debit_note"]
    },
    "hsn": {
        "description": "HSN Summary",
        "required_fields": ["hsn_code", "taxable_value"],
        "conditions": lambda row: row.get("hsn_code") is not None
    },
    "doc_iss": {
        "description": "Documents Issued",
        "required_fields": ["invoice_no"],
        "conditions": lambda row: row.get("invoice_no") is not None
    }
}

# Schema versions supported
SCHEMA_VERSIONS = {
    "GST3.1.6": {
        "version": "3.1.6",
        "description": "GST Portal version 3.1.6",
        "sections": ["b2b", "b2cl", "b2cs", "cdnr", "cdnur", "exp", "at", "atadj", "hsn", "doc_iss", "eco_reg", "eco_unreg"]
    }
}
