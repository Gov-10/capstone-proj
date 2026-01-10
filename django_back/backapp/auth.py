from ninja.security import HttpBearer
import os
from dotenv import load_dotenv
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import datetime
import requests

load_dotenv()

COGNITO_REGION = os.getenv("COGNITO_REGION")
USER_POOL_ID = os.getenv("USER_POOL_ID")
USER_POOL_CLIENT_ID = os.getenv("USER_POOL_CLIENT_ID")

JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"

# Initialize JWKS with fallback for missing config
try:
    JWKS = requests.get(JWKS_URL, timeout=5).json()["keys"] if COGNITO_REGION and USER_POOL_ID else []
except Exception as e:
    print(f"Warning: Could not fetch JWKS from Cognito: {e}")
    JWKS = []


def validate_token(token: str):

    # ---- 1. Extract KID --------
    headers = jwt.get_unverified_headers(token)
    kid = headers["kid"]

    # ---- 2. Find JWKS key --------
    jwt_key = next((key for key in JWKS if key["kid"] == kid), None)
    if jwt_key is None:
        raise Exception("Public key not found in JWKS")

    # ---- 3. Get token claims (unverified) --------
    unverified = jwt.get_unverified_claims(token)

    # ---- 4. Check expiration --------
    if unverified["exp"] < datetime.utcnow().timestamp():
        raise Exception("Token is expired")

    # ---- 5. Validate audience/client_id --------
    # Cognito sometimes uses "aud", sometimes "client_id"
    aud = unverified.get("aud") or unverified.get("client_id")
    if aud != USER_POOL_CLIENT_ID:
        raise Exception(f"Invalid audience: expected {USER_POOL_CLIENT_ID}, got {aud}")

    # ---- 6. Final Signature Verification --------
    message, encoded_signature = token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode())

    public_key = jwk.construct(jwt_key)

    if not public_key.verify(message.encode(), decoded_signature):
        raise Exception("Signature verification failed")

    return unverified


class CustomAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            claims = validate_token(token)
            print("VALIDATED CLAIMS: ", claims)
            return claims
        except Exception as e:
            print("AUTH ERROR:", e)
            return None
