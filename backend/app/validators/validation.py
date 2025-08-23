from datetime import datetime

def validate_non_empty_string(value: str, field_name: str) -> str:
    """Require non-empty string."""
    if not isinstance(value, str) or value.strip() == '':
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value

def validate_non_negative_int(value: int, field_name: str) -> int:
    """Require int >= 0."""
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value

def validate_date_string(value: str, field_name: str, fmt: str = "%Y-%m-%d") -> str:
    """Require valid date string."""
    try:
        datetime.strptime(value, fmt)
    except Exception:
        raise ValueError(f"{field_name} must be a valid date in format {fmt}.")
    return value

def validate_context_dict(value, field_name: str = "context") -> dict:
    """Require dict."""
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict.")
    return value