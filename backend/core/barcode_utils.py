"""
EATGOOD — Barcode Validation & Normalization Service
Standard GS1 check-digit verification and format identification.
Supports EAN-13, EAN-8, UPC-A, and UPC-E without losing leading zeros.
"""

import re
from typing import Any


def clean_barcode(barcode: Any) -> str:
    """Strips whitespace, hyphens, and periods while strictly preserving leading zeros as string."""
    if barcode is None:
        return ""
    return re.sub(r'[\s\-.]', '', str(barcode).strip())

def normalize_upc_to_ean13(upc_a_barcode: str) -> str:
    """
    Normalizes a 12-digit UPC-A to 13-digit EAN-13 by prepending '0'.
    The GS1 check digit remains identical.
    """
    cleaned = clean_barcode(upc_a_barcode)
    if len(cleaned) == 12:
        return "0" + cleaned
    return cleaned

def calculate_gs1_check_digit(digits_str: str) -> int:
    """
    Computes the standard GS1 check digit for a string of digits (without the check digit).
    Uses the alternating 3x / 1x weighting starting from the rightmost data digit.
    Formula:
      Sum = sum(d * (3 if pos_from_right is odd else 1))
      Check digit = (10 - (Sum % 10)) % 10
    """
    total = 0
    # Process from right to left with alternating weights: 3, 1, 3, 1, ...
    for i, char in enumerate(reversed(digits_str)):
        weight = 3 if (i % 2 == 0) else 1
        total += int(char) * weight
    remainder = total % 10
    return 0 if remainder == 0 else (10 - remainder)


def validate_barcode(barcode: str, strict: bool = False) -> dict[str, Any]:
    """
    Validates and normalizes retail barcode strings:
    - Preserves leading zeros as string.
    - Identifies standard retail format: EAN-13, EAN-8, UPC-A, UPC-E.
    - Evaluates standard GS1 modulo-10 check digit.
    - Accommodates retail datasets where check digits may not have been strictly validated.

    Args:
        barcode: Raw barcode string or numeric representation.
        strict: If True, check-digit mismatch marks is_valid as False.
                If False, standard length (8, 12, 13, 14 digits) is accepted with check_digit_valid flag.

    Returns:
        dict containing:
            is_valid: bool
            normalized: str
            format: str ("EAN-13", "EAN-8", "UPC-A", "UPC-E", etc.)
            check_digit_valid: bool
            expected_check_digit: Optional[int]
            actual_check_digit: Optional[int]
            error: Optional[str]
    """
    if barcode is None or str(barcode).strip() == "":
        return {
            "is_valid": False,
            "normalized": "",
            "format": "INVALID",
            "check_digit_valid": False,
            "expected_check_digit": None,
            "actual_check_digit": None,
            "error": "Barcode input is empty."
        }

    # Normalize: strip whitespace, dashes, and periods
    cleaned = re.sub(r'[\s\-.]', '', str(barcode).strip())

    if not cleaned.isdigit():
        return {
            "is_valid": False,
            "normalized": cleaned,
            "format": "INVALID",
            "check_digit_valid": False,
            "expected_check_digit": None,
            "actual_check_digit": None,
            "error": "Barcode must contain only numeric digits."
        }

    length = len(cleaned)

    # 1. EAN-13 (13 digits)
    if length == 13:
        data_part = cleaned[:12]
        expected_check = calculate_gs1_check_digit(data_part)
        actual_check = int(cleaned[12])
        cd_valid = (expected_check == actual_check)
        is_ok = cd_valid if strict else True
        err = None if cd_valid else f"Check digit mismatch (expected {expected_check}, found {actual_check})."

        return {
            "is_valid": is_ok,
            "normalized": cleaned,
            "format": "EAN-13",
            "check_digit_valid": cd_valid,
            "expected_check_digit": expected_check,
            "actual_check_digit": actual_check,
            "error": err
        }

    # 2. UPC-A (12 digits)
    elif length == 12:
        data_part = cleaned[:11]
        expected_check = calculate_gs1_check_digit(data_part)
        actual_check = int(cleaned[11])
        cd_valid = (expected_check == actual_check)
        is_ok = cd_valid if strict else True
        err = None if cd_valid else f"Check digit mismatch (expected {expected_check}, found {actual_check})."

        return {
            "is_valid": is_ok,
            "normalized": cleaned,
            "format": "UPC-A",
            "check_digit_valid": cd_valid,
            "expected_check_digit": expected_check,
            "actual_check_digit": actual_check,
            "error": err
        }

    # 3. EAN-8 (8 digits)
    elif length == 8:
        data_part = cleaned[:7]
        expected_check = calculate_gs1_check_digit(data_part)
        actual_check = int(cleaned[7])
        cd_valid = (expected_check == actual_check)
        is_ok = cd_valid if strict else True
        err = None if cd_valid else f"Check digit mismatch (expected {expected_check}, found {actual_check})."

        return {
            "is_valid": is_ok,
            "normalized": cleaned,
            "format": "EAN-8",
            "check_digit_valid": cd_valid,
            "expected_check_digit": expected_check,
            "actual_check_digit": actual_check,
            "error": err
        }

    # 4. UPC-E (6 digits)
    elif length == 6:
        return {
            "is_valid": True,
            "normalized": cleaned,
            "format": "UPC-E",
            "check_digit_valid": True,
            "expected_check_digit": None,
            "actual_check_digit": None,
            "error": None
        }

    # 5. GTIN-14 / Shipping containers (14 digits)
    elif length == 14:
        data_part = cleaned[:13]
        expected_check = calculate_gs1_check_digit(data_part)
        actual_check = int(cleaned[13])
        cd_valid = (expected_check == actual_check)
        return {
            "is_valid": cd_valid if strict else True,
            "normalized": cleaned,
            "format": "GTIN-14",
            "check_digit_valid": cd_valid,
            "expected_check_digit": expected_check,
            "actual_check_digit": actual_check,
            "error": None if cd_valid else f"Check digit mismatch (expected {expected_check}, found {actual_check})."
        }

    # Generic numeric length
    elif 4 <= length <= 18:
        return {
            "is_valid": True,
            "normalized": cleaned,
            "format": f"GENERIC-{length}",
            "check_digit_valid": False,
            "expected_check_digit": None,
            "actual_check_digit": None,
            "error": None
        }

    return {
        "is_valid": False,
        "normalized": cleaned,
        "format": "INVALID",
        "check_digit_valid": False,
        "expected_check_digit": None,
        "actual_check_digit": None,
        "error": f"Invalid barcode length ({length} digits)."
    }
