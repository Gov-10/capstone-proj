"""
Request tracking and progress monitoring for async operations.
"""

import uuid
from typing import Optional, Dict
from enum import Enum
from datetime import datetime
from pydantic import BaseModel


class ProcessingStatus(str, Enum):
    """Status of document processing"""
    QUEUED = "queued"
    VALIDATING = "validating"
    EXTRACTING_TEXT = "extracting_text"
    CHUNKING = "chunking"
    SUMMARIZING = "summarizing"
    ANALYZING = "analyzing"
    CACHING = "caching"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressUpdate(BaseModel):
    """Progress update for long-running operations"""
    request_id: str
    status: ProcessingStatus
    progress_percent: int  # 0-100
    current_step: str
    estimated_time_remaining: Optional[int] = None  # seconds
    message: Optional[str] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class RequestTracker:
    """Track request progress and metadata"""

    def __init__(self):
        self.requests: Dict[str, Dict] = {}

    def create_request(self, user_email: str, file_key: str, file_size: int) -> str:
        """Create a new request tracker"""
        request_id = str(uuid.uuid4())
        self.requests[request_id] = {
            "user_email": user_email,
            "file_key": file_key,
            "file_size": file_size,
            "created_at": datetime.utcnow(),
            "status": ProcessingStatus.QUEUED,
            "progress": 0,
            "current_step": "Preparing for analysis...",
            "chunks_total": 0,
            "chunks_processed": 0,
        }
        return request_id

    def update_progress(
        self,
        request_id: str,
        status: ProcessingStatus,
        progress: int,
        current_step: str,
        chunks_total: int = 0,
        chunks_processed: int = 0
    ) -> Optional[ProgressUpdate]:
        """Update request progress"""
        if request_id not in self.requests:
            return None

        req = self.requests[request_id]
        req["status"] = status
        req["progress"] = min(progress, 100)
        req["current_step"] = current_step
        if chunks_total > 0:
            req["chunks_total"] = chunks_total
        if chunks_processed > 0:
            req["chunks_processed"] = chunks_processed

        # Estimate remaining time based on progress
        elapsed = (datetime.utcnow() - req["created_at"]).total_seconds()
        if req["progress"] > 0:
            total_estimated = (elapsed / req["progress"]) * 100
            remaining = int(total_estimated - elapsed)
        else:
            remaining = None

        return ProgressUpdate(
            request_id=request_id,
            status=status,
            progress_percent=req["progress"],
            current_step=current_step,
            estimated_time_remaining=remaining,
            message=f"{current_step} ({chunks_processed}/{chunks_total} chunks)"
            if chunks_total > 0
            else current_step
        )

    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get request details"""
        return self.requests.get(request_id)

    def mark_completed(self, request_id: str):
        """Mark request as completed"""
        if request_id in self.requests:
            self.requests[request_id]["status"] = ProcessingStatus.COMPLETED
            self.requests[request_id]["progress"] = 100

    def mark_failed(self, request_id: str, error: str):
        """Mark request as failed"""
        if request_id in self.requests:
            self.requests[request_id]["status"] = ProcessingStatus.FAILED
            self.requests[request_id]["error"] = error

    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Remove requests older than max_age_hours"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        to_delete = [
            rid for rid, data in self.requests.items()
            if data["created_at"] < cutoff
        ]
        for rid in to_delete:
            del self.requests[rid]


# Global request tracker instance
request_tracker = RequestTracker()


def estimate_processing_time(file_size_mb: float, num_chunks: int) -> int:
    """
    Estimate processing time in seconds based on file size and chunk count.

    Assumptions:
    - 1 second per MB for PDF parsing
    - 5-10 seconds per chunk for AI summarization
    - 10 seconds for final analysis
    """
    parsing_time = int(file_size_mb)
    summarization_time = int(num_chunks * 7)  # average 7 seconds per chunk
    final_analysis_time = 10

    return parsing_time + summarization_time + final_analysis_time
