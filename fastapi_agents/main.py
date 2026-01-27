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
from typing import Union, Any

load_dotenv()

tesseract_path = os.getenv("TESSERACT_PATH")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

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

try:
    from database import get_session, SessionDep, User, ChatHistory
    HAS_DB = True
except Exception:
    def get_session():
        return None

def _init_pubsub():
    try:
        from google.cloud import pubsub_v1 as _pubsub
        return _pubsub
    except Exception:
        return None

try:
    pubsub_v1 = _init_pubsub()
    HAS_PUBSUB = pubsub_v1 is not None
except Exception:
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
except Exception:
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
    if not HAS_PUBSUB:
        return

    try:
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = os.getenv("SUBSCRIBER_PATH")

        if not subscription_path:
            return

        def callback(message: Any):
            app.state.mess = message.data.decode("utf-8")
            message.ack()

        streaming_pull_feature = subscriber.subscribe(subscription_path, callback=callback)

        try:
            streaming_pull_feature.result()
        except Exception:
            pass
    except Exception:
        pass

@app.on_event("startup")
def launch_subscriber():
    thread = threading.Thread(target=pubsub_listener, daemon=True)
    thread.start()

def _extract_text_from_page(page):
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

def extract_pdf_text_hybrid(pdf, min_chars_per_page=40, ocr_dpi=300, ocr_lang=None):
    if ocr_lang is None:
        ocr_lang = os.getenv("OCR_LANG", "eng")

    final_text_parts = []

    for page in pdf:
        text = _extract_text_from_page(page)
        final_text_parts.append(text)

    return "\n".join(final_text_parts)

def chunk_text(text, chunk_size=4000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def summarize_chunk(chunk: str):
    from agents.agent import get_agent
    res = get_agent()(chunk)
    return res.message["content"][0]["text"].strip()

def final_legal_analysis(chunk_summaries):
    from agents.agent import get_agent
    res = get_agent()(json.dumps(chunk_summaries))
    return res.message["content"][0]["text"].strip()

@app.get("/status", response_model=StatusResponse)
async def check(
    user=Depends(get_current_user),
    session=Depends(get_session)
):

    if app.state.mess is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document processing request found"
        )

    try:
        payload = json.loads(app.state.mess)
        status_request = StatusRequest(**payload)
        file_key = status_request.file_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    bucket = os.getenv("AWS_BUCKET_NAME")
    if not bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AWS bucket configuration missing"
        )

    try:
        obj = s3.get_object(Bucket=bucket, Key=file_key)
        content = obj["Body"].read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    max_size = 50 * 1024 * 1024

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum limit of 50MB"
        )

    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        pdf_text = extract_pdf_text_hybrid(pdf)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    if not pdf_text or len(pdf_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Insufficient readable content"
        )

    content_hash = hashlib.sha256(pdf_text.encode("utf-8")).hexdigest()

    cached = redis_client.get(content_hash) if redis_client else None
    if cached:
        app.state.mess = None
        return StatusResponse(response=cached, cache=True)

    chunks = chunk_text(pdf_text)
    summaries = [summarize_chunk(chunk) for chunk in chunks]

    final_output = final_legal_analysis(summaries)

    if redis_client:
        redis_client.set(content_hash, final_output, ex=86400)

    app.state.mess = None

    return StatusResponse(response=final_output)

@app.get("/health", response_model=HealthResponse)
async def health_check():
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
