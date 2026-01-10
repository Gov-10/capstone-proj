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

# Lazy-load JWKS to avoid network requests at import time
JWKS = None

def _get_jwks():
    """Fetch JWKS only when needed."""
    global JWKS
    if JWKS is not None:
        return JWKS
    if not COGNITO_REGION or not USER_POOL_ID:
        raise RuntimeError("COGNITO_REGION or USER_POOL_ID not set in environment.")
    jwks_url = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
    try:
        JWKS = requests.get(jwks_url, timeout=5).json()["keys"]
    except Exception as e:
        raise RuntimeError(f"Failed to fetch JWKS: {e}")
    return JWKS

def validate_token(token: str):
    """
    Validate JWT token from AWS Cognito.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token claims

    Raises:
        ValueError: If token validation fails
    """
    try:
         # FIX: Use lazy-loaded JWKS instead of global JWKS directly
        keys = _get_jwks()

        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")
        if not kid:
            raise ValueError("Token missing 'kid' header")

        jwt_key = next((key for key in keys if key["kid"] == kid), None)
        if jwt_key is None:
            raise ValueError("Public key not found in JWKS")

        unverified = jwt.get_unverified_claims(token)
        if unverified.get("exp", 0) < datetime.utcnow().timestamp():
            raise ValueError("Token is expired")

        aud = unverified.get("aud") or unverified.get("client_id")
        if aud != USER_POOL_CLIENT_ID:
            raise ValueError(f"Invalid audience: expected {USER_POOL_CLIENT_ID}, got {aud}")

        message, encoded_signature = token.rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode())
        public_key = jwk.construct(jwt_key)
        if not public_key.verify(message.encode(), decoded_signature):
            raise ValueError("Signature verification failed")

        return unverified
    except Exception as e:
        raise ValueError(f"Token validation failed: {str(e)}")
    

class CustomAuth:
    def authenticate(self, request, token):
        try:
            claims = validate_token(token)
            return claims
        except ValueError:
            return None

auth_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials=Depends(auth_scheme)):
    token = credentials.credentials
    auth = CustomAuth()
    user  = auth.authenticate(None, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user