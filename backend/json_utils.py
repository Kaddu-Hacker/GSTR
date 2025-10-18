"""
Custom JSON encoder to handle special float values (NaN, Infinity) and datetime objects
"""
import json
import math
from typing import Any
from datetime import datetime, date

def sanitize_value(value: Any) -> Any:
    """
    Convert non-JSON-serializable values to JSON-compatible types
    - NaN and Infinity to None
    - datetime to ISO format string
    - date to ISO format string
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, date):
        return value.isoformat()
    return value

def sanitize_dict(data: dict) -> dict:
    """
    Recursively sanitize all values in a dictionary
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [sanitize_dict(item) if isinstance(item, dict) else sanitize_value(item) for item in value]
        else:
            result[key] = sanitize_value(value)
    
    return result

def safe_json_response(data: Any) -> dict:
    """
    Prepare data for JSON response by sanitizing all values
    """
    if isinstance(data, dict):
        return sanitize_dict(data)
    elif isinstance(data, list):
        return [sanitize_dict(item) if isinstance(item, dict) else sanitize_value(item) for item in data]
    return data
