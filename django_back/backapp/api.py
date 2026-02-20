from ninja import NinjaAPI
from .auth import CustomAuth
from .schema import HelloTestResponse, GetSignedUrl, ChatHistoryOut, ErrorOut
import uuid, boto3
import os
import logging
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from datetime import datetime
import json
from typing import List
from .errors import (
    raise_validation_error, raise_s3_error, raise_pubsub_error, raise_internal_error, ApiError
)
from .validation import (
    validate_file_format, validate_content_type, validate_file_size,
    get_format_suggestions, get_size_suggestions
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api = NinjaAPI()
load_dotenv()

# Initialize S3 with error handling
try:
    s3 = boto3.client(
        's3',
        region_name=os.getenv("COGNITO_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    # Test S3 connection
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if bucket_name:
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.info("S3 connection successful")
        except Exception as e:
            logger.warning(f"S3 bucket check failed: {str(e)}")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {str(e)}")
    s3 = None

# Initialize Pub/Sub with error handling
try:
    RUNNING_IN_GCP = os.getenv("RUNNING_IN_GCP") == "1"
    if not RUNNING_IN_GCP:
        credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    else:
        logger.info("Running in GCP environment, using default credentials.")

    publisher = pubsub_v1.PublisherClient()
    topic_path = os.getenv("TOPIC_PATH")
    logger.info("Pub/Sub client initialized")
except Exception as e:
    logger.error(f"Failed to initialize Pub/Sub: {str(e)}")
    publisher = None
    topic_path = None

@api.post("/secure-hello", auth=CustomAuth())
def secure_hello(request, payload: HelloTestResponse):
    return {"secure_hello": payload.text}

@api.post("/get-upload-url", auth=CustomAuth())
def get_upload_url(request, payload: GetSignedUrl):
    """
    Generate a presigned URL for uploading documents to S3.
    Validates file format and provides detailed error messages.
    """
    try:
        # Validate file format
        if not validate_file_format(payload.file_name):
            logger.warning(f"Invalid file format: {payload.file_name}")
            raise_validation_error(
                message="Unsupported file format",
                details=f"File '{payload.file_name}' has an unsupported extension",
                suggestions=get_format_suggestions()
            )

        # Validate content type
        if not validate_content_type(payload.content_type):
            logger.warning(f"Invalid content type: {payload.content_type}")
            raise_validation_error(
                message="Invalid file type",
                details=f"Content type '{payload.content_type}' is not supported",
                suggestions=get_format_suggestions()
            )

        # Check filename length (S3 limitation)
        if len(payload.file_name) > 200:
            raise_validation_error(
                message="Filename is too long",
                details="Filename must be 200 characters or less",
                suggestions=["Try renaming the file with a shorter name"]
            )

        # Check for invalid characters in filename
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\']
        if any(char in payload.file_name for char in invalid_chars):
            raise_validation_error(
                message="Filename contains invalid characters",
                details=f"Filename cannot contain: {', '.join(invalid_chars)}",
                suggestions=["Rename the file without special characters"]
            )

        if not s3:
            logger.error("S3 client not initialized")
            raise_s3_error(
                message="File storage service is unavailable",
                details="S3 client failed to initialize"
            )

        user = request.auth
        user_id = user.get('sub')
        if not user_id:
            logger.warning("User ID not found in auth token")
            raise_validation_error(
                message="Invalid authentication",
                details="User ID not found in token",
                suggestions=["Log in again and try uploading"]
            )

        # Generate file key
        file_id = str(uuid.uuid4())
        key = f"documents/{user_id}/{file_id}-{payload.file_name}"

        # Generate presigned URL
        try:
            presigned_url = s3.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': os.getenv("S3_BUCKET_NAME"),
                    "Key": key,
                    "ContentType": payload.content_type
                },
                ExpiresIn=600  # 10 minutes
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise_s3_error(
                message="Failed to generate upload link",
                details=str(e)
            )

        # Prepare metadata for Pub/Sub
        metadata = {
            "user_id": user_id,
            "user_email": user.get("email", "unknown"),
            "file_key": key,
            "file_name": payload.file_name,
            "content_type": payload.content_type,
            "correlation_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Publish to Pub/Sub
        if not publisher or not topic_path:
            logger.error("Pub/Sub not initialized")
            raise_pubsub_error(
                message="Document queuing service is unavailable",
                details="Pub/Sub client not initialized"
            )

        try:
            message_data = json.dumps(metadata).encode("utf-8")
            future = publisher.publish(topic_path, message_data)
            message_id = future.result()
            logger.info(f"Published Pub/Sub message: {message_id} for user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to publish to Pub/Sub: {str(e)}")
            raise_pubsub_error(
                message="Failed to queue document for analysis",
                details=str(e)
            )

        return {
            "success": True,
            "upload_url": presigned_url,
            "file_key": key,
            "expires_in": 600,
            "message": "Upload URL generated successfully. You have 10 minutes to upload the file."
        }

    except Exception as e:
        logger.error(f"Unexpected error in get_upload_url: {str(e)}")
        raise_internal_error(details=str(e))

from .models import ChatHistory
@api.get("/chat-history", response=List[ChatHistoryOut], auth=CustomAuth())
def chat_history(request):
    """
    Get user's analysis history with error handling.
    Returns up to 50 most recent analyses.
    """
    try:
        user = request.auth
        user_email = user.get('email')

        if not user_email:
            logger.warning("User email not found in auth token")
            raise_validation_error(
                message="Invalid authentication",
                details="User email not found",
                suggestions=["Log in again"]
            )

        logger.info(f"Fetching chat history for user: {user_email}")

        # Fetch history from database
        ch = ChatHistory.objects.filter(
            user_email=user_email
        ).order_by("-timestamp")[:50]

        logger.info(f"Found {len(ch)} history records for user: {user_email}")

        return ch

    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise_internal_error(
            message="Failed to retrieve analysis history",
            details=str(e)
        )
