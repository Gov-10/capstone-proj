import os
from dotenv import load_dotenv
from jose import jwt, jwk
from jose.utils import base64url_decode
from datetime import datetime
import requests
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
load_dotenv()
COGNITO_REGION = os.getenv("COGNITO_REGION")
USER_POOL_ID = os.getenv("USER_POOL_ID")
USER_POOL_CLIENT_ID = os.getenv("USER_POOL_CLIENT_ID")

JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"

# Gracefully handle missing Cognito configuration
JWKS = []
COGNITO_AVAILABLE = False
try:
    if COGNITO_REGION and USER_POOL_ID:
        JWKS = requests.get(JWKS_URL).json()["keys"]
        COGNITO_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not fetch JWKS from Cognito: {e}. Running in dev mode without auth.")
    COGNITO_AVAILABLE = False

def validate_token(token: str):
    # In dev mode without Cognito, allow any token
    if not COGNITO_AVAILABLE:
        return {"sub": "dev-user", "email": "dev@example.com"}

    headers = jwt.get_unverified_headers(token)
    kid = headers["kid"]
    jwt_key = next((key for key in JWKS if key["kid"] == kid), None)
    if jwt_key is None:
        raise Exception("Public key not found in JWKS")
    unverified = jwt.get_unverified_claims(token)
    if unverified["exp"] < datetime.utcnow().timestamp():
        raise Exception("Token is expired")
    aud = unverified.get("aud") or unverified.get("client_id")
    if aud != USER_POOL_CLIENT_ID:
        raise Exception(f"Invalid audience: expected {USER_POOL_CLIENT_ID}, got {aud}")
    message, encoded_signature = token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode())
    public_key = jwk.construct(jwt_key)
    if not public_key.verify(message.encode(), decoded_signature):
        raise Exception("Signature verification failed")
    return unverified

class CustomAuth:
    def authenticate(self, request, token):
        try: 
            claims = validate_token(token)
            return claims
        except Exception as e:
            return None

auth_scheme = HTTPBearer()
def get_current_user(credentials: HTTPAuthorizationCredentials=Depends(auth_scheme)):
    token = credentials.credentials
    auth = CustomAuth()
    user  = auth.authenticate(None, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user