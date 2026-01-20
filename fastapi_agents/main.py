from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from google.cloud import pubsub_v1
import threading
import json
from fastapi import Depends
from auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables, ChatHistory, User, SessionDep
from redis import Redis
import boto3
import fitz
import hashlib
from schemas import StatusRequest, StatusResponse, ErrorResponse, HealthResponse, ValidationErrorResponse
from pydantic import ValidationError
from typing import Union
import time
from agents.langgraph_agent import analyze_legal_document

load_dotenv()
redis_client = Redis(
    host=os.getenv("REDIS_URL"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("COGNITO_REGION")
)


app = FastAPI(
    title="Legal Document Analysis API",
    description="AI-powered legal document analysis service",
    version="1.0.0"
)
app.state.mess = None

# Exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    errors = {}
    for error in exc.errors():
        field_name = ".".join(str(loc) for loc in error["loc"]) if error["loc"] else "unknown"
        errors[field_name] = error["msg"]
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ValidationErrorResponse(
            errors=errors,
            code="VALIDATION_ERROR"
        ).model_dump()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": "HTTP_EXCEPTION"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "details": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None
        }
    )

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
    print("🎉 Pub/Sub listener running in background thread!")


def extract_pdf_text(pdf):
    """Extract text from PDF with fallback for legal/complex PDFs."""

    final_text = ""

    for page in pdf:
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

    return final_text


def validate_document_text(text: str) -> tuple[bool, str]:
    """
    Validate extracted document text before processing (Phase 6: Edge case handling)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Minimum length check
    if not text or len(text.strip()) < 50:
        return False, "Document contains insufficient readable text (minimum 50 characters required)"
    
    # Maximum length check (prevent timeout on extremely large docs)
    max_length = 500000  # 500K characters limit
    if len(text) > max_length:
        return False, f"Document too large (maximum {max_length} characters allowed)"
    
    # Check if document is mostly readable text (not corrupted)
    printable_chars = sum(1 for c in text if c.isprintable() or c.isspace())
    if printable_chars / len(text) < 0.8:  # At least 80% printable
        return False, "Document appears to be corrupted or contains unreadable content"
    
    return True, ""


@app.get("/status", response_model=StatusResponse)
async def check(user=Depends(get_current_user), session: SessionDep = None) -> StatusResponse:
    """
    Process uploaded PDF document and return legal analysis.

    - **Returns**: Legal document analysis or error response
    - **Requires**: Valid authentication token
    """
    try:
        # Validate PubSub message exists
        if app.state.mess is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No document processing request found"
            )

        print("RAW:", repr(app.state.mess))

        # Parse and validate the PubSub message
        try:
            payload = json.loads(app.state.mess)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in PubSub message: {str(e)}"
            )

        # Validate the payload structure
        try:
            status_request = StatusRequest(**payload)
            file_key = status_request.file_key
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid request data: {str(e)}"
            )

        bucket = os.getenv("AWS_BUCKET_NAME")
        if not bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AWS bucket configuration missing"
            )

        # Download file from S3
        try:
            obj = s3.get_object(Bucket=bucket, Key=file_key)
            content = obj["Body"].read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to retrieve file from S3: {str(e)}"
            )

        # Validate file size (max 50MB)
        max_size = 50 * 1024 * 1024 
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds maximum limit of 50MB"
            )

        # Open and validate PDF
        try:
            pdf = fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to open PDF: {str(e)}"
            )

        # Extract text from PDF
        try:
            pdf_text = extract_pdf_text(pdf)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )

        #Enhanced validation for edge cases
        is_valid, validation_error = validate_document_text(pdf_text)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=validation_error
            )

        # Check cache
        content_hash = hashlib.sha256(pdf_text.encode("utf-8")).hexdigest()
        cached = redis_client.get(content_hash)
        if cached:
            print("🚀 Cache HIT:", content_hash)
            app.state.mess = None
            return StatusResponse(response=cached, cache=True)

        print("❌ Cache MISS:", content_hash)

        # Ensure user exists in database
        try:
            existing_user = session.get(User, user["email"])
            if not existing_user:
                session.add(User(email=user["email"]))
                session.commit()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        

        print("🚀 Running LangGraph Legal Analysis...")
        try:
            start_time = time.time()
            
            # Use LangGraph agent for analysis
            final_output = analyze_legal_document(pdf_text)
            
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000 
            
            print(f"  Agent analysis completed in {processing_time:.2f}ms")
            print(f"   References found: {final_output.get('metadata', {}).get('references_found', 0)}")
            print(f"   API calls made: {final_output.get('metadata', {}).get('api_calls_made', 0)}")
            print(f"   Legal sections: {len(final_output.get('legal_sections', []))}")
            
            # Convert to JSON string for storage and caching
            final_output_str = json.dumps(final_output, indent=2)
            
        except Exception as e:
            print(f" Agent analysis failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to perform legal analysis: {str(e)}"
            )
        
        # Validate output
        if not final_output_str or len(final_output_str.strip()) < 50:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Legal analysis produced insufficient output"
            )

        # Cache the result
        try:
            redis_client.set(content_hash, final_output_str, ex=60 * 60 * 24) 
        except Exception as e:
            print(f"  Warning: Failed to cache result: {str(e)}")

        # Save to database
        try:
            new_history = ChatHistory(
                user_email=user["email"],
                file_key=file_key,
                response=final_output_str
            )
            session.add(new_history)
            session.commit()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save chat history: {str(e)}"
            )

        # Reset message
        app.state.mess = None

        return StatusResponse(response=final_output_str)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify service status.

    - **Returns**: Service health information
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get("/health/langgraph")
async def langgraph_health_check():
    """
    LangGraph-specific health check endpoint.
    Verifies that LangGraph agent is properly configured and functional.
    
    - **Returns**: LangGraph health information and configuration status
    """
    try:
        # Check API keys
        groq_configured = bool(os.getenv("GROQ_API_KEY"))
        gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
        
        # Try to create graph (lightweight check)
        from agents.langgraph_agent import create_legal_analysis_graph
        graph = create_legal_analysis_graph()
        graph_compiled = graph is not None
        
        health_status = {
            "status": "healthy" if (groq_configured and gemini_configured and graph_compiled) else "degraded",
            "version": "1.0.0",
            "langgraph": {
                "graph_compiled": graph_compiled,
                "groq_api_configured": groq_configured,
                "gemini_api_configured": gemini_configured,
                "nodes": ["deduction", "fetch", "summarization", "formatting"]
            }
        }
        
        if not (groq_configured and gemini_configured):
            health_status["warnings"] = []
            if not groq_configured:
                health_status["warnings"].append("GROQ_API_KEY not configured")
            if not gemini_configured:
                health_status["warnings"].append("GEMINI_API_KEY not configured")
        
        return JSONResponse(content=health_status)
        
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "unhealthy",
                "error": str(e),
                "langgraph": {"graph_compiled": False}
            }
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://capstone-proj-green.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
