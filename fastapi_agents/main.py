from fastapi import FastAPI, HTTPException, status
import os
from dotenv import load_dotenv
from google.cloud import pubsub_v1
import threading
import json
from agents.agent import get_agent
from fastapi import Depends
from auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, ChatHistory, User, SessionDep
from redis import Redis
import boto3
import fitz
import hashlib
import logging
from datetime import datetime
from errors import (
    FileProcessingError, DocumentValidationError, AnalysisError, ErrorCode,
    validate_file_format, validate_file_size, get_format_suggestions, get_size_suggestions
)
from progress import ProcessingStatus, request_tracker, estimate_processing_time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize clients with error handling
try:
    redis_client = Redis(
        host=os.getenv("REDIS_URL", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info("Redis connection successful")
except Exception as e:
    logger.warning(f"Redis connection failed: {str(e)}. Caching disabled.")
    redis_client = None

try:
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("COGNITO_REGION", "us-east-1")
    )
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {str(e)}")
    raise

app = FastAPI(title="Legal Summarizer API", version="1.0.0")
app.state.mess = None

def pubsub_listener():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = os.getenv("SUBSCRIBER_PATH")

    def callback(message: pubsub_v1.subscriber.message.Message):
        app.state.mess = message.data.decode("utf-8")
        print(f"Received: {message.data.decode('utf-8')}")
        message.ack()

    print(f"Pub/Sub: Listening on {subscription_path}...")
    streaming_pull_feature = subscriber.subscribe(subscription_path, callback=callback)

    try:
        streaming_pull_feature.result()
    except Exception as e:
        print(f"Crashed: {e}")


@app.on_event("startup")
def launch_subscriber():
    # create_db_and_tables()
    thread = threading.Thread(target=pubsub_listener, daemon=True)
    thread.start()
    print("[STARTUP] Pub/Sub listener running in background thread!")


def extract_pdf_text(pdf, request_id: str = None):
    """
    Extract text from PDF with fallback strategies for legal/complex PDFs.
    Raises FileProcessingError if text cannot be extracted.
    """
    final_text = ""

    try:
        for page_num, page in enumerate(pdf):
            try:
                text = page.get_text("text").strip()
                if not text:
                    blocks = page.get_text("blocks")
                    if isinstance(blocks, list):
                        text = "\n".join(
                            blk[4] for blk in blocks
                            if isinstance(blk, list) and len(blk) > 4
                        ).strip()
                if not text:
                    raw = page.get_text("rawdict")
                    if "blocks" in raw:
                        text = "\n".join(
                            blk.get("text", "")
                            for blk in raw["blocks"]
                            if blk.get("type") == 0
                        ).strip()

                final_text += text + "\n"

                if request_id:
                    progress = int((page_num + 1) / len(pdf) * 30)  # 30% for extraction
                    request_tracker.update_progress(
                        request_id,
                        ProcessingStatus.EXTRACTING_TEXT,
                        progress,
                        f"Extracting text from page {page_num + 1}/{len(pdf)}..."
                    )

            except Exception as e:
                logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                continue

        if not final_text.strip():
            raise FileProcessingError(
                error_code=ErrorCode.NO_TEXT_EXTRACTED,
                message="Unable to extract readable text from the PDF",
                details="The PDF may be image-based, password-protected, or corrupted",
                suggestions=[
                    "Ensure the PDF contains searchable text, not just images",
                    "Try removing any password protection from the PDF",
                    "Verify the PDF file is not corrupted",
                    "For image-based PDFs, consider using OCR (coming soon)"
                ],
                request_id=request_id
            )

        return final_text

    except FileProcessingError:
        raise
    except Exception as e:
        logger.error(f"PDF text extraction failed: {str(e)}")
        raise FileProcessingError(
            error_code=ErrorCode.FILE_CORRUPTED,
            message="Failed to process the PDF file",
            details=f"Technical error: {str(e)}",
            suggestions=get_format_suggestions(),
            request_id=request_id
        )


def chunk_text(text, chunk_size=4000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def summarize_chunk(chunk: str):
    prompt = f"""
You are a Legal Document Chunk Summarizer.
Summarize the following part of a legal document factually,
without legal advice or opinions.

Chunk:
---------------------
{chunk}
---------------------
"""
    res = get_agent()(prompt)
    return res.message["content"][0]["text"].strip()


def final_legal_analysis(chunk_summaries):
    prompt = f"""
You are a Legal Document Intelligence Agent.

You will receive summarized chunks of a long legal document.
Using ONLY the information in those summaries, generate:

1. A complete overall summary
2. Identified Indian legal sections (IT Act, IPC, Constitution etc.)
3. Factual context/explanation for each section
4. Highlight red flags (ambiguities, missing data, contradictions)
5. Do NOT provide legal advice
6. End with: "Disclaimer: This is an automated analysis, not legal advice."

Chunk Summaries:
-------------------------
{json.dumps(chunk_summaries, indent=2)}
-------------------------
"""
    res = get_agent()(prompt)
    return res.message["content"][0]["text"].strip()


@app.get("/status")
async def check(user=Depends(get_current_user), session: SessionDep = None):
    """
    Analyze uploaded legal document with comprehensive error handling.
    Returns detailed analysis with error messages if processing fails.
    """
    request_id = None

    try:
        # Validate payload
        if not app.state.mess:
            raise DocumentValidationError(
                error_code=ErrorCode.INVALID_REQUEST,
                message="No document to analyze",
                details="File metadata not received from upload service",
                suggestions=[
                    "Try uploading the document again",
                    "Ensure the upload completed successfully",
                    "Check your internet connection"
                ]
            )

        payload = json.loads(app.state.mess)
        file_key = payload.get("file_key")
        user_email = user.get("email")

        if not file_key:
            raise DocumentValidationError(
                error_code=ErrorCode.INVALID_REQUEST,
                message="Missing file reference",
                details="File key not found in upload metadata",
                suggestions=["Try uploading the document again"]
            )

        # Create request tracker
        bucket_name = os.getenv("AWS_BUCKET_NAME", "legal-summarizer-docs")
        request_id = request_tracker.create_request(user_email, file_key, 0)

        logger.info(f"Processing document: {request_id} from user: {user_email}")
        request_tracker.update_progress(
            request_id,
            ProcessingStatus.VALIDATING,
            5,
            "Downloading document from storage..."
        )

        # Download from S3
        try:
            obj = s3.get_object(Bucket=bucket_name, Key=file_key)
            content = obj["Body"].read()
            file_size = len(content)

            # Validate file size
            is_valid, size_msg = validate_file_size(file_size)
            if not is_valid:
                raise DocumentValidationError(
                    error_code=ErrorCode.FILE_TOO_LARGE,
                    message=size_msg,
                    details=f"File size: {file_size / (1024*1024):.2f} MB",
                    suggestions=get_size_suggestions(),
                    request_id=request_id
                )

        except DocumentValidationError:
            raise
        except Exception as e:
            logger.error(f"S3 download failed: {str(e)}")
            raise DocumentValidationError(
                error_code=ErrorCode.S3_ERROR,
                message="Failed to download document from storage",
                details=f"Error: {str(e)}",
                suggestions=[
                    "Try uploading the document again",
                    "Ensure the file was successfully uploaded"
                ],
                request_id=request_id
            )

        # Open and validate PDF
        request_tracker.update_progress(
            request_id,
            ProcessingStatus.VALIDATING,
            10,
            "Validating PDF structure..."
        )

        try:
            pdf = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            logger.error(f"PDF open failed: {str(e)}")
            raise DocumentValidationError(
                error_code=ErrorCode.FILE_CORRUPTED,
                message="The file is not a valid PDF",
                details=f"PDF parsing error: {str(e)}",
                suggestions=get_format_suggestions() + [
                    "Verify the file is a valid PDF document"
                ],
                request_id=request_id
            )

        # Extract text with progress tracking
        request_tracker.update_progress(
            request_id,
            ProcessingStatus.EXTRACTING_TEXT,
            15,
            "Extracting text from document..."
        )

        pdf_text = extract_pdf_text(pdf, request_id)

        request_tracker.update_progress(
            request_id,
            ProcessingStatus.CHUNKING,
            35,
            "Preparing document for analysis..."
        )

        # Check cache before processing
        content_hash = hashlib.sha256(pdf_text.encode("utf-8")).hexdigest()
        if redis_client:
            try:
                cached = redis_client.get(content_hash)
                if cached:
                    logger.info(f"Cache HIT: {content_hash}")
                    request_tracker.mark_completed(request_id)
                    app.state.mess = None
                    return {
                        "success": True,
                        "response": cached,
                        "cache": True,
                        "request_id": request_id
                    }
            except Exception as e:
                logger.warning(f"Cache lookup failed: {str(e)}")

        logger.info(f"Cache MISS: {content_hash}")

        # Process document
        try:
            existing_user = session.get(User, user_email)
            if not existing_user:
                session.add(User(email=user_email))
                session.commit()
        except Exception as e:
            logger.error(f"Database user creation failed: {str(e)}")

        # Chunk text
        chunks = chunk_text(pdf_text)
        num_chunks = len(chunks)
        estimated_time = estimate_processing_time(file_size / (1024*1024), num_chunks)

        request_tracker.update_progress(
            request_id,
            ProcessingStatus.SUMMARIZING,
            40,
            f"Analyzing document ({num_chunks} sections)...",
            chunks_total=num_chunks,
            chunks_processed=0
        )

        logger.info(f"Processing {num_chunks} chunks (est. {estimated_time}s)")

        # Summarize chunks with error handling
        chunk_summaries = []
        for index, chunk in enumerate(chunks):
            try:
                summary = summarize_chunk(chunk)
                chunk_summaries.append(summary)

                progress = 40 + int((index + 1) / num_chunks * 40)  # 40-80%
                request_tracker.update_progress(
                    request_id,
                    ProcessingStatus.SUMMARIZING,
                    progress,
                    f"Analyzing section {index + 1}/{num_chunks}...",
                    chunks_total=num_chunks,
                    chunks_processed=index + 1
                )

            except Exception as e:
                logger.error(f"Chunk {index + 1} summarization failed: {str(e)}")
                raise AnalysisError(
                    message="Failed to analyze document sections",
                    details=f"Error processing section {index + 1}/{num_chunks}: {str(e)}",
                    suggestions=[
                        "Try uploading a shorter document",
                        "Ensure the document is in English or uses standard legal terminology",
                        "Try again later"
                    ],
                    request_id=request_id
                )

        # Final legal analysis
        request_tracker.update_progress(
            request_id,
            ProcessingStatus.ANALYZING,
            80,
            "Performing legal analysis..."
        )

        try:
            final_output = final_legal_analysis(chunk_summaries)
        except Exception as e:
            logger.error(f"Final analysis failed: {str(e)}")
            raise AnalysisError(
                message="Failed to complete legal analysis",
                details=str(e),
                request_id=request_id
            )

        # Cache and store results
        request_tracker.update_progress(
            request_id,
            ProcessingStatus.CACHING,
            90,
            "Saving results..."
        )

        try:
            if redis_client:
                redis_client.set(content_hash, final_output, ex=60 * 60 * 24)
        except Exception as e:
            logger.warning(f"Failed to cache result: {str(e)}")

        try:
            new_history = ChatHistory(
                user_email=user_email,
                file_key=file_key,
                response=final_output
            )
            session.add(new_history)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to save analysis history: {str(e)}")

        # Reset message and mark complete
        app.state.mess = None
        request_tracker.mark_completed(request_id)

        return {
            "success": True,
            "response": final_output,
            "cache": False,
            "request_id": request_id
        }

    except DocumentValidationError as e:
        logger.error(f"Document validation error: {e.error_response.error_code}")
        if request_id:
            request_tracker.mark_failed(request_id, e.error_response.error_code)
        raise
    except FileProcessingError as e:
        logger.error(f"File processing error: {e.error_response.error_code}")
        if request_id:
            request_tracker.mark_failed(request_id, e.error_response.error_code)
        raise
    except AnalysisError as e:
        logger.error(f"Analysis error: {e.error_response.error_code}")
        if request_id:
            request_tracker.mark_failed(request_id, e.error_response.error_code)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {str(e)}")
        if request_id:
            request_tracker.mark_failed(request_id, "UNEXPECTED_ERROR")
        raise AnalysisError(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            details=str(e),
            request_id=request_id
        )

@app.get("/progress/{request_id}")
async def get_progress(request_id: str, user=Depends(get_current_user)):
    """
    Get progress of document analysis.
    Returns current processing status, progress percentage, and estimated time remaining.
    """
    request_data = request_tracker.get_request(request_id)

    if not request_data:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "REQUEST_NOT_FOUND",
                "message": "Analysis request not found",
                "request_id": request_id
            }
        )

    # Verify user owns this request
    if request_data["user_email"] != user.get("email"):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "UNAUTHORIZED",
                "message": "You don't have access to this request"
            }
        )

    elapsed = (datetime.utcnow() - request_data["created_at"]).total_seconds()
    if request_data["progress"] > 0:
        total_estimated = (elapsed / request_data["progress"]) * 100
        remaining = int(total_estimated - elapsed)
    else:
        remaining = None

    return {
        "request_id": request_id,
        "status": request_data["status"],
        "progress_percent": request_data["progress"],
        "current_step": request_data["current_step"],
        "chunks_processed": request_data.get("chunks_processed", 0),
        "chunks_total": request_data.get("chunks_total", 0),
        "elapsed_seconds": int(elapsed),
        "estimated_time_remaining": remaining,
        "error": request_data.get("error")
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint with service status.
    """
    status = {
        "status": "healthy",
        "services": {
            "redis": "unavailable",
            "s3": "unavailable"
        }
    }

    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            status["services"]["redis"] = "available"
        except Exception as e:
            logger.warning(f"Redis health check failed: {str(e)}")

    # Check S3 (basic check)
    try:
        s3.head_bucket(Bucket=os.getenv("AWS_BUCKET_NAME", "legal-summarizer-docs"))
        status["services"]["s3"] = "available"
    except Exception as e:
        logger.warning(f"S3 health check failed: {str(e)}")
        status["status"] = "degraded"

    return status
        "https://capstone-proj-green.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
