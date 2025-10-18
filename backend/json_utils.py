"""
Custom JSON encoder to handle special float values (NaN, Infinity)
"""
import json
import math
from typing import Any

def sanitize_float(value: Any) -> Any:
    """
    Convert NaN and Infinity to None for JSON compatibility
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value

def sanitize_dict(data: dict) -> dict:
    """
    Recursively sanitize all float values in a dictionary
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [sanitize_dict(item) if isinstance(item, dict) else sanitize_float(item) for item in value]
        else:
            result[key] = sanitize_float(value)
    
    return result

def safe_json_response(data: Any) -> dict:
    """
    Prepare data for JSON response by sanitizing floats
    """
    if isinstance(data, dict):
        return sanitize_dict(data)
    elif isinstance(data, list):
        return [sanitize_dict(item) if isinstance(item, dict) else sanitize_float(item) for item in data]
    return data
