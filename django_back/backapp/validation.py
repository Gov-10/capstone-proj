"""
File validation utilities for Django backend.
"""

from typing import Tuple, List

# File validation constants
SUPPORTED_FORMATS = [".pdf"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MIN_FILE_SIZE = 1024  # 1 KB

# MIME type mappings
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
}


def validate_file_format(filename: str) -> bool:
    """Check if file format is supported"""
    if not filename:
        return False
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    return f".{ext}" in SUPPORTED_FORMATS


def validate_content_type(content_type: str) -> bool:
    """Check if content type is valid"""
    if not content_type:
        return False
    return content_type.lower() in SUPPORTED_MIME_TYPES


def validate_file_size(file_size: int) -> Tuple[bool, str]:
    """
    Validate file size.
    Returns (is_valid, message)
    """
    if file_size < MIN_FILE_SIZE:
        return False, f"File is too small (minimum {MIN_FILE_SIZE} bytes)"
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File is too large (maximum {max_mb:.1f} MB)"
    return True, "File size is valid"


def get_format_suggestions() -> List[str]:
    """Get suggestions for file format issues"""
    return [
        f"Supported formats: {', '.join(SUPPORTED_FORMATS)}",
        "Ensure the PDF is not password protected",
        "Ensure the PDF contains readable text, not just images"
    ]


def get_size_suggestions() -> List[str]:
    """Get suggestions for file size issues"""
    max_mb = MAX_FILE_SIZE / (1024 * 1024)
    return [
        f"Maximum file size: {max_mb:.1f} MB",
        "Try compressing the PDF or splitting it into smaller parts",
        "Ensure there are no extra images or embedded media"
    ]
