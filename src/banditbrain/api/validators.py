from datetime import datetime


def validate_non_empty_string(value: str, field_name: str) -> str:
    """Require non-empty string."""
    if not isinstance(value, str) or value.strip() == "":
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
        raise ValueError(f"{field_name} must be a valid date in format {fmt}.") from None
    return value


def validate_context_dict(value, field_name: str = "context") -> dict:
    """Require dict."""
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict.")
    return value


def validate_non_negative_float(value: float, field_name: str) -> int:
    """Require float >= 0.0"""
    if not isinstance(value, float) or value < 0.0:
        raise ValueError(f"{field_name} must be a non-negative float.")
    return value


def validate_algorithm(value: str, field_name: str = "method") -> str:
    """Checks if the algorithm is one of the allowed values."""
    allowed = ["eg", "ucb", "ts", "softmax"]
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(allowed)}.")
    return value


def validate_epsilon(value: float, field_name: str = "epsilon") -> float:
    """Validates if epsilon is between 0 and 1."""
    if not isinstance(value, float) or not (0.0 <= value <= 1.0):
        raise ValueError(f"{field_name} must be a float between 0 and 1.")
    return value


def validate_binary_reward(value: float, field_name: str = "reward") -> float:
    """Require reward to be exactly 0.0 or 1.0 (click-equivalent; see ROADMAP non-goals)."""
    if not isinstance(value, float) or value not in (0.0, 1.0):
        raise ValueError(f"{field_name} must be 0.0 or 1.0.")
    return value


def validate_allocation_bound(value: float, field_name: str) -> float:
    """Require an allocation floor/cap to be a float in [0, 1]."""
    if not isinstance(value, float) or not (0.0 <= value <= 1.0):
        raise ValueError(f"{field_name} must be a float between 0 and 1.")
    return value


def validate_batch_size(items: list, max_size: int, field_name: str = "batch") -> list:
    """Require a batch/list to not exceed max_size items (upload size guardrail)."""
    if len(items) > max_size:
        raise ValueError(f"{field_name} of {len(items)} items exceeds the {max_size}-item limit.")
    return items
