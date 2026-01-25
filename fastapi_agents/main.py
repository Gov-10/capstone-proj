from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import boto3
from dotenv import load_dotenv
import threading
import json
from PIL import Image, ImageEnhance, ImageFilter
import fitz
import pytesseract
import hashlib
from schemas import StatusRequest, StatusResponse, ErrorResponse, HealthResponse, ValidationErrorResponse
from pydantic import ValidationError
from typing import Union,Any


#COMMENTS TO BE ADDED LATER
load_dotenv()

# Configure Tesseract path from .env (Windows)
tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Lazy imports for optional dependencies - wrapped safely
HAS_PUBSUB = False
HAS_REDIS = False
HAS_S3 = False
HAS_AGENT = False
HAS_DB = False

pubsub_v1 = None
redis_client = None
s3 = None
get_agent = None
Session = None
SessionDep = None
User = None
ChatHistory = None


# Optional database wiring
try:
    from database import get_session, SessionDep, User, ChatHistory
    HAS_DB = True
except Exception as e:
    print(f"[INFO] Database not available: {type(e).__name__}. DB operations disabled.")
    def get_session():
        return None

def _init_pubsub():
    try:
        from google.cloud import pubsub_v1 as _pubsub
        return _pubsub
    except Exception:
        print("[INFO] Google Cloud Pub/Sub not installed. Pub/Sub listener disabled.")
        return None

try:
    pubsub_v1 = _init_pubsub()
    HAS_PUBSUB = pubsub_v1 is not None
except Exception:
    print("[INFO] Pub/Sub initialization failed.")
    pubsub_v1 = None
    HAS_PUBSUB = False

try:
    from redis import Redis
    redis_client = Redis(
        host=os.getenv("REDIS_URL", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )
    HAS_REDIS = True
except Exception as e:
    print(f"[INFO] Redis not available: {type(e).__name__}. Caching disabled.")
    redis_client = None
    HAS_REDIS = False

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
    """Listen to Pub/Sub messages (only if dependencies available)."""
    if not HAS_PUBSUB:
        print("⚠️  Pub/Sub listener not started - dependency not installed.")
        return
    
    try:
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = os.getenv("SUBSCRIBER_PATH")
        
        if not subscription_path:
            print("⚠️  SUBSCRIBER_PATH not configured. Pub/Sub listener disabled.")
            return

        def callback(message: Any):
            app.state.mess = message.data.decode("utf-8")
            print(f"Received: {message.data.decode('utf-8')}")
            message.ack()

        print(f"Pub/Sub: Listening on {subscription_path}...")
        streaming_pull_feature = subscriber.subscribe(subscription_path, callback=callback)

        try:
            streaming_pull_feature.result()
        except Exception as e:
            print(f"Pub/Sub crashed: {e}")
    except Exception as e:
        print(f"⚠️  Pub/Sub listener failed to start: {e}")

@app.on_event("startup")
def launch_subscriber():
    # create_db_and_tables()
    thread = threading.Thread(target=pubsub_listener, daemon=True)
    thread.start()
    print("🎉 Pub/Sub listener running in background thread!")

def _extract_text_from_page(page):
    """Try multiple PyMuPDF text modes for a single page."""
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
        if isinstance(raw, dict) and "blocks" in raw:
            text = "\n".join(
                blk.get("text", "")
                for blk in raw["blocks"]
                if blk.get("type") == 0
            ).strip()
    return text


def _preprocess_image_for_ocr(img, mode="default"):
    """Enhance image quality before OCR to improve text extraction accuracy.
    
    Args:
        img: PIL Image
        mode: "default", "light", or "aggressive"
    """
    from PIL import ImageOps
    
    # Convert to grayscale
    img = img.convert('L')
    
    if mode == "light":
        # Minimal processing - good for already decent quality scans
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
    elif mode == "aggressive":
        # Heavy processing - for very poor quality scans
        img = ImageOps.autocontrast(img)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.5)
        img = img.filter(ImageFilter.SHARPEN)
        img = img.filter(ImageFilter.MedianFilter(size=3))  # Remove noise
        
    else:  # default
        # Balanced processing
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)
        img = ImageOps.autocontrast(img)
    
    return img


def _ocr_with_fallback(img, ocr_lang="eng", page_num=0):
    """Try OCR with multiple configurations until text is extracted."""
    
    print(f"[OCR] Attempting extraction for page {page_num + 1}")
    
    # Strategy 1: Default preprocessing with PSM 3 (auto page segmentation)
    try:
        processed = _preprocess_image_for_ocr(img, mode="default")
        config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(processed, lang=ocr_lang, config=config).strip()
        if len(text) > 10:  # Got meaningful text
            print(f"[OCR] Strategy 1 succeeded: {len(text)} chars")
            return text
        print(f"[OCR] Strategy 1 result: {len(text)} chars (trying next)")
    except Exception as e:
        print(f"[OCR] Strategy 1 failed: {e}")
    
    # Strategy 2: Light preprocessing with PSM 6 (uniform block of text)
    try:
        processed = _preprocess_image_for_ocr(img, mode="light")
        config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(processed, lang=ocr_lang, config=config).strip()
        if len(text) > 10:
            print(f"[OCR] Strategy 2 succeeded: {len(text)} chars")
            return text
        print(f"[OCR] Strategy 2 result: {len(text)} chars (trying next)")
    except Exception as e:
        print(f"[OCR] Strategy 2 failed: {e}")
    
    # Strategy 3: Aggressive preprocessing with PSM 1 (auto with OSD - orientation detection)
    try:
        processed = _preprocess_image_for_ocr(img, mode="aggressive")
        config = r'--oem 3 --psm 1'
        text = pytesseract.image_to_string(processed, lang=ocr_lang, config=config).strip()
        if len(text) > 0:
            print(f"[OCR] Strategy 3 succeeded: {len(text)} chars")
            return text
        print(f"[OCR] Strategy 3 result: {len(text)} chars (trying next)")
    except Exception as e:
        print(f"[OCR] Strategy 3 failed: {e}")
    
    # Strategy 4: Raw image, no preprocessing
    try:
        gray = img.convert('L')
        config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(gray, lang=ocr_lang, config=config).strip()
        if len(text) > 10:
            print(f"[OCR] Strategy 4 succeeded: {len(text)} chars")
            return text
        print(f"[OCR] Strategy 4 (raw) result: {len(text)} chars (trying next)")
    except Exception as e:
        print(f"[OCR] Strategy 4 failed: {e}")
    
    # Strategy 5: Upscale to higher resolution (2x) for better detail
    try:
        from PIL import ImageOps
        # Upscale 2x using high-quality resampling
        w, h = img.size
        upscaled = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        processed = _preprocess_image_for_ocr(upscaled, mode="default")
        config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(processed, lang=ocr_lang, config=config).strip()
        if len(text) > 10:
            print(f"[OCR] Strategy 5 (2x upscale) succeeded: {len(text)} chars")
            return text
        print(f"[OCR] Strategy 5 (2x upscale) result: {len(text)} chars (trying next)")
    except Exception as e:
        print(f"[OCR] Strategy 5 failed: {e}")
    
    # Strategy 6: Deskew + denoise for skewed/noisy scans
    try:
        from PIL import ImageOps, ImageFilter
        gray = img.convert('L')
        # Apply median filter to reduce noise
        denoised = gray.filter(ImageFilter.MedianFilter(size=3))
        # Auto-contrast
        processed = ImageOps.autocontrast(denoised)
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(processed)
        processed = enhancer.enhance(2.5)
        config = r'--oem 3 --psm 4'  # PSM 4: single column of text
        text = pytesseract.image_to_string(processed, lang=ocr_lang, config=config).strip()
        if len(text) > 0:
            print(f"[OCR] Strategy 6 (denoise) succeeded: {len(text)} chars")
            return text
        print(f"[OCR] Strategy 6 (denoise) result: {len(text)} chars")
    except Exception as e:
        print(f"[OCR] Strategy 6 failed: {e}")
    
    print(f"[OCR] All strategies exhausted for page {page_num + 1}")
    return ""


def extract_pdf_text_hybrid(pdf,min_chars_per_page=40, ocr_dpi=300, ocr_lang=None):
    """Extract text from PDF with fallback to render the page to an image and OCR it for legal/complex PDFs."""

    if ocr_lang is None:
        ocr_lang = os.getenv("OCR_LANG", "eng")
    final_text_parts = []

    for page in pdf:
        text = _extract_text_from_page(page)
        if len(text.strip()) >= min_chars_per_page:
            final_text_parts.append(text)
            continue

        # OCR fallback for this page with multi-strategy approach
        try:
            zoom = ocr_dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            # Try multiple OCR strategies until we get text
            ocr_text = _ocr_with_fallback(img, ocr_lang, page_num=page.number)
            final_text_parts.append(ocr_text or text)
        except Exception as e:
            print(f"OCR error on page {page.number}: {e}")
            final_text_parts.append(text)

    return "\n".join(final_text_parts)


def extract_pdf_text_hybrid_with_info(pdf, min_chars_per_page=40, ocr_dpi=300, ocr_lang=None):
    """Extract text with PyMuPDF first; if too little text on a page, fallback to OCR.
    Returns combined text and per-page method info.
    """

    if ocr_lang is None:
        ocr_lang = os.getenv("OCR_LANG", "eng")

    final_text_parts = []
    pages_info = []

    for page in pdf:
        text = _extract_text_from_page(page)
        method = "pymupdf"
        out_text = text

        if len(text.strip()) < min_chars_per_page:
            try:
                zoom = ocr_dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                
                # Try multiple OCR strategies until we get text
                ocr_text = _ocr_with_fallback(img, ocr_lang, page_num=page.number)
                out_text = ocr_text or text
                method = "ocr"
            except Exception as e:
                print(f"OCR error on page {page.number}: {e}")
                method = "pymupdf"

        final_text_parts.append(out_text)
        pages_info.append({
            "page": page.number + 1,
            "method": method,
            "chars": len(out_text)
        })

    return "\n".join(final_text_parts), pages_info


def chunk_text(text, chunk_size=4000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def summarize_chunk(chunk: str):
    from agents.agent import get_agent
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
    from agents.agent import get_agent
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


@app.get("/status", response_model=StatusResponse)
async def check(
    user=Depends(get_current_user),
    session=Depends(get_session)
) -> StatusResponse:
    """
    Process uploaded PDF document and return legal analysis.

    - **Returns**: Legal document analysis or error response
    - **Requires**: Valid authentication token
    """
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
    max_size = 50 * 1024 * 1024  # 50MB
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
        pdf_text = extract_pdf_text_hybrid(pdf)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )

    # Validate extracted text
    if not pdf_text or len(pdf_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded document contains insufficient readable text (minimum 50 characters required)"
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
    print("📌 Splitting PDF into chunks...")
    try:
        chunks = chunk_text(pdf_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document chunks: {str(e)}"
        )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document could not be split into processable chunks"
        )

    print(f"📄 Total Chunks: {len(chunks)}")

    # Process chunks
    chunk_summaries = []
    for index, chunk in enumerate(chunks):
        print(f"🔹 Summarizing Chunk {index + 1}/{len(chunks)}...")
        try:
            summary = summarize_chunk(chunk)
            if not summary or len(summary.strip()) < 10:
                print(f"⚠️  Warning: Chunk {index + 1} produced insufficient summary")
                continue
            chunk_summaries.append(summary)
        except Exception as e:
            print(f"⚠️  Warning: Failed to summarize chunk {index + 1}: {str(e)}")
            continue

    if not chunk_summaries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to generate summaries for any document chunks"
        )

    print("🔍 Running Final Legal Analysis...")
    try:
        final_output = final_legal_analysis(chunk_summaries)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform legal analysis: {str(e)}"
        )

    if not final_output or len(final_output.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Legal analysis produced insufficient output"
        )

    # Cache the result
    try:
        if redis_client:
            redis_client.set(content_hash, final_output, ex=60 * 60 * 24)  # 24 hours
    except Exception as e:
        print(f"⚠️  Warning: Failed to cache result: {str(e)}")

    # Save to database
    try:
        if HAS_DB and session and ChatHistory:
            new_history = ChatHistory(
                user_email=user["email"],
                file_key=file_key,
                response=final_output
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

    return StatusResponse(response=final_output)


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
