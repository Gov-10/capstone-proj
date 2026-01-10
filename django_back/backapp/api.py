from ninja import NinjaAPI
from .auth import CustomAuth
from .schema import HelloTestResponse, GetSignedUrl, ChatHistoryOut
import uuid, boto3
import os
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from datetime import datetime
import json
from typing import List
api = NinjaAPI()
load_dotenv()
s3 = boto3.client(
    's3', 
    region_name= os.getenv("COGNITO_REGION"),
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
)
RUNNING_IN_GCP = os.getenv("RUNNING_IN_GCP") == "1"
bucket_name = os.getenv("S3_BUCKET_NAME")
if not RUNNING_IN_GCP:
    credentials_path = os.getenv("GCP_CREDENTIALS_PATH")
    if credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
else:
    print("Running in GCP environment, using default credentials.")
publisher = pubsub_v1.PublisherClient()
topic_path = os.getenv("TOPIC_PATH")
@api.post("/secure-hello", auth=CustomAuth())
def secure_hello(request, payload: HelloTestResponse):
    return {"secure_hello": payload.text}

@api.post("/get-upload-url", auth=CustomAuth())
def get_upload_url(request, payload: GetSignedUrl):
    user = request.auth
    user_id = user['sub']
    file_id = str(uuid.uuid4())
    key = f"videos/{user_id}/{file_id}-{payload.file_name}"
    presigned_url = s3.generate_presigned_url(
        ClientMethod = 'put_object', 
        Params = {
            'Bucket': bucket_name, 
            "Key" : key, 
            "ContentType": payload.content_type
        }, 
        ExpiresIn = 600
    )
    data = {
        "user_id": user_id,
        "file_key": key,
        "file_name": payload.file_name,
        "content_type": payload.content_type, 
        "correlation_id": str(uuid.uuid4()), 
        "timestamp": datetime.utcnow().isoformat()
    }
    data = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic_path, data)
    print(f"Published message ID: {future.result()}")
    return {"upload_url": presigned_url, "file_key": key}

from .models import ChatHistory
@api.get("/chat-history", response=List[ChatHistoryOut], auth=CustomAuth())
def chat_history(request):
    user = request.auth
    user_email = user['email']
    ch = ChatHistory.objects.filter(user_email=user_email).order_by("-timestamp")[:50]
    return ch
