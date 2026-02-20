from ninja import Schema
from datetime import datetime
from typing import Optional, List

class HelloTestResponse(Schema):
    text: str

class GetSignedUrl(Schema):
    file_name: str
    content_type: str

class ChatHistoryOut(Schema):
    timestamp: datetime
    response: str

class ErrorOut(Schema):
    """Standardized error response schema"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[str] = None
    suggestions: List[str] = []
    timestamp: datetime
