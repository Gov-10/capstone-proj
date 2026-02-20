"""
Comprehensive error handling for Django backend.
"""

from ninja import NinjaAPI
from ninja.errors import HttpError
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
from datetime import datetime


class ErrorCode(str, Enum):
    """Django API error codes"""
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    S3_ERROR = "S3_ERROR"
    PUBSUB_ERROR = "PUBSUB_ERROR"
    AUTH_FAILED = "AUTH_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"


class ApiError(BaseModel):
    """Standard API error response"""
    success: bool = False
    error_code: ErrorCode
    message: str
    details: Optional[str] = None
    suggestions: List[str] = []
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


def raise_validation_error(
    message: str,
    details: str = None,
    suggestions: List[str] = None
):
    """Raise a validation error with standardized format"""
    error = ApiError(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=details,
        suggestions=suggestions or []
    )
    raise HttpError(400, error.dict())


def raise_s3_error(
    message: str = "Failed to interact with file storage",
    details: str = None
):
    """Raise an S3 error"""
    error = ApiError(
        error_code=ErrorCode.S3_ERROR,
        message=message,
        details=details,
        suggestions=[
            "Try uploading the document again",
            "Ensure the file is not corrupted",
            "Check your internet connection"
        ]
    )
    raise HttpError(500, error.dict())


def raise_pubsub_error(
    message: str = "Failed to queue document for analysis",
    details: str = None
):
    """Raise a Pub/Sub error"""
    error = ApiError(
        error_code=ErrorCode.PUBSUB_ERROR,
        message=message,
        details=details,
        suggestions=[
            "Try uploading the document again",
            "If the problem persists, contact support"
        ]
    )
    raise HttpError(500, error.dict())


def raise_internal_error(
    message: str = "An internal error occurred",
    details: str = None
):
    """Raise an internal error"""
    error = ApiError(
        error_code=ErrorCode.INTERNAL_ERROR,
        message=message,
        details=details,
        suggestions=[
            "Try again later",
            "If the problem persists, contact support"
        ]
    )
    raise HttpError(500, error.dict())
