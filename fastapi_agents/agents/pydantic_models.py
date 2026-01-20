"""
Pydantic models for legal document analysis validation
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class LegalSection(BaseModel):
    """Model for individual legal section in output"""
    reference: str = Field(..., description="Legal reference (e.g., 'Section 302 IPC')")
    context: str = Field(..., description="Context or explanation of the section")
    relevance: str = Field(..., description="Relevance to the document")
    
    @field_validator('reference', 'context', 'relevance')
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v


class OutputMetadata(BaseModel):
    """Model for output metadata"""
    processing_time_ms: float = Field(..., ge=0, description="Total processing time in milliseconds")
    references_found: int = Field(..., ge=0, description="Number of legal references found")
    api_calls_made: int = Field(..., ge=0, description="Total API calls made")
    api_success_rate: float = Field(..., ge=0, le=100, description="API success rate percentage")


class LegalAnalysisOutput(BaseModel):
    """Complete output schema for legal document analysis"""
    summary: str = Field(..., min_length=10, description="Overall analysis summary")
    legal_sections: List[LegalSection] = Field(default_factory=list, description="List of legal sections")
    red_flags: List[str] = Field(default_factory=list, description="List of potential concerns")
    disclaimer: str = Field(..., min_length=30, description="Legal disclaimer")
    metadata: OutputMetadata = Field(..., description="Processing metadata")
    
    @field_validator('summary', 'disclaimer')
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v
