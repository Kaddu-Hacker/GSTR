"""Decimal arithmetic utilities for precise tax calculations"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional
import re

# Decimal constants
ZERO = Decimal('0')
ONE = Decimal('1')
TWO = Decimal('2')
HUNDRED = Decimal('100')


def parse_money(value: Union[str, int, float, Decimal, None]) -> Decimal:
    """
    Parse monetary value to Decimal, handling various formats
    
    Examples:
        "₹1,234.56" -> Decimal('1234.56')
        "(100.50)" -> Decimal('-100.50')
        "1234" -> Decimal('1234')
        "" -> Decimal('0')
    """
    if value is None or value == "":
        return ZERO
    
    if isinstance(value, Decimal):
        return value
    
    try:
        # Convert to string
        s = str(value).strip()
        
        if not s:
            return ZERO
        
        # Handle parentheses as negative (accounting format)
        is_negative = False
        if s.startswith('(') and s.endswith(')'):
            is_negative = True
            s = s[1:-1]
        
        # Remove currency symbols, commas, spaces
        s = re.sub(r'[₹$€£Rs,\s]+', '', s)
        
        # Convert to Decimal
        result = Decimal(s)
        
        if is_negative:
            result = -result
        
        return result
    
    except (ValueError, InvalidOperation):
        return ZERO


def round_decimal(value: Decimal, places: int = 2) -> Decimal:
    """
    Round Decimal to specified decimal places using ROUND_HALF_UP
    """
    if places == 2:
        quantizer = Decimal('0.01')
    elif places == 4:
        quantizer = Decimal('0.0001')
    elif places == 6:
        quantizer = Decimal('0.000001')
    else:
        quantizer = Decimal(f"0.{'0' * places}")
    
    return value.quantize(quantizer, rounding=ROUND_HALF_UP)


def compute_tax(
    taxable_value: Decimal,
    gst_rate: Decimal,
    seller_state_code: str,
    place_of_supply_code: str
) -> dict:
    """
    Compute tax split (CGST/SGST/IGST) with precise Decimal arithmetic
    
    Args:
        taxable_value: Taxable amount
        gst_rate: GST rate (e.g., 18 for 18%)
        seller_state_code: 2-digit seller state code
        place_of_supply_code: 2-digit place of supply code
    
    Returns:
        dict with tax_amount_raw, cgst, sgst, igst, rounding_diff, is_intra_state
    """
    # Calculate raw tax amount
    tax_amount_raw = taxable_value * gst_rate / HUNDRED
    
    # Determine if intra-state or inter-state
    is_intra_state = seller_state_code == place_of_supply_code
    
    if is_intra_state:
        # Split into CGST and SGST
        cgst = round_decimal(tax_amount_raw / TWO)
        sgst = round_decimal(tax_amount_raw - cgst)  # Remainder to avoid rounding issues
        igst = ZERO
    else:
        # All goes to IGST
        igst = round_decimal(tax_amount_raw)
        cgst = ZERO
        sgst = ZERO
    
    # Calculate rounding difference
    total_tax = cgst + sgst + igst
    rounding_diff = round_decimal(tax_amount_raw) - total_tax
    
    return {
        "tax_amount_raw": tax_amount_raw,
        "tax_amount": float(total_tax),
        "cgst_amount": float(cgst),
        "sgst_amount": float(sgst),
        "igst_amount": float(igst),
        "rounding_diff": float(rounding_diff),
        "is_intra_state": is_intra_state
    }


def aggregate_decimals(values: list, round_result: bool = True) -> Decimal:
    """
    Aggregate list of Decimal values
    """
    total = sum((parse_money(v) for v in values), ZERO)
    if round_result:
        return round_decimal(total)
    return total


def format_for_json(value: Decimal, places: int = 2) -> float:
    """
    Format Decimal for JSON output as float with specified decimal places
    """
    rounded = round_decimal(value, places)
    return float(rounded)
