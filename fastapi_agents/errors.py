"""
Comprehensive error handling for Legal Summarizer API.
Provides detailed error responses with recovery suggestions.
"""

from fastapi import HTTPException, status
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class ErrorCode(str, Enum):
    """Standardized error codes for client-side handling"""
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    NO_TEXT_EXTRACTED = "NO_TEXT_EXTRACTED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    S3_ERROR = "S3_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """Standard error response format"""
    success: bool = False
    error_code: ErrorCode
    message: str
    details: Optional[str] = None
    suggestions: List[str] = []
    timestamp: datetime = None
    request_id: Optional[str] = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class DocumentValidationError(HTTPException):
    """Raised when document validation fails"""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: str = None,
        suggestions: List[str] = None,
        request_id: str = None
    ):
        self.error_response = ErrorResponse(
            error_code=error_code,
            message=message,
            details=details,
            suggestions=suggestions or [],
            request_id=request_id
        )
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=self.error_response.dict()
        )


class FileProcessingError(HTTPException):
    """Raised when file processing fails"""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: str = None,
        suggestions: List[str] = None,
        request_id: str = None
    ):
        self.error_response = ErrorResponse(
            error_code=error_code,
            message=message,
            details=details,
            suggestions=suggestions or [],
            request_id=request_id
        )
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=self.error_response.dict()
        )


class AnalysisError(HTTPException):
    """Raised when analysis fails"""
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.ANALYSIS_FAILED,
        message: str = "Failed to complete legal analysis",
        details: str = None,
        suggestions: List[str] = None,
        request_id: str = None
    ):
        if suggestions is None:
            suggestions = [
                "Try uploading the document again",
                "Ensure the document is in PDF format",
                "Check that the file is not corrupted"
            ]

        self.error_response = ErrorResponse(
            error_code=error_code,
            message=message,
            details=details,
            suggestions=suggestions,
            request_id=request_id
        )
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=self.error_response.dict()
        )


class AuthenticationError(HTTPException):
    """Raised when authentication fails"""
    def __init__(
        self,
        message: str = "Authentication failed",
        details: str = None,
        request_id: str = None
    ):
        self.error_response = ErrorResponse(
            error_code=ErrorCode.AUTH_FAILED,
            message=message,
            details=details,
            suggestions=["Please log in again", "Ensure your token is valid"],
            request_id=request_id
        )
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=self.error_response.dict()
        )


class ConfigurationError(Exception):
    """Raised when environment configuration is invalid"""
    pass


# File validation constants
SUPPORTED_FORMATS = [".pdf"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MIN_FILE_SIZE = 1024  # 1 KB
MIN_TEXT_LENGTH = 50  # Minimum readable text


def validate_file_format(filename: str) -> bool:
    """Validate file format"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    return f".{ext}" in SUPPORTED_FORMATS


def validate_file_size(file_size: int) -> tuple[bool, str]:
    """Validate file size and return (is_valid, message)"""
    if file_size < MIN_FILE_SIZE:
        return False, f"File is too small (minimum {MIN_FILE_SIZE} bytes)"
    if file_size > MAX_FILE_SIZE:
        return False, f"File is too large (maximum {MAX_FILE_SIZE / (1024*1024):.1f} MB)"
    return True, "File size is valid"


def get_format_suggestions() -> List[str]:
    """Get file format suggestions"""
    return [
        f"Supported formats: {', '.join(SUPPORTED_FORMATS)}",
        "Ensure the PDF is not password protected",
        "Ensure the PDF contains readable text, not just images"
    ]


def get_size_suggestions() -> List[str]:
    """Get file size suggestions"""
    return [
        f"Maximum file size: {MAX_FILE_SIZE / (1024*1024):.1f} MB",
        "Try compressing the PDF or splitting it into smaller parts",
        "Ensure there are no extra images or embedded media"
    ]
