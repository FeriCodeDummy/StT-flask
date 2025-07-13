import os
import requests
from functools import wraps
from flask import request, jsonify
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

TENANT_ID  = os.environ["AZURE_TENANT_ID"]
CLIENT_ID  = os.environ["AZURE_CLIENT_ID"]
ISSUER     = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
JWKS_URI   = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
ALGORITHMS = ["RS256"]
# shranimo jwt 

try:
    _jwks = requests.get(JWKS_URI).json()
except Exception as e:
    raise RuntimeError(f"Failed to fetch JWKS from {JWKS_URI}: {e}")

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", None)
        if not auth:
            return jsonify({"error": "Missing Authorization header"}), 401

        parts = auth.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            return jsonify({"error": "Invalid Authorization header"}), 401

        token = parts[1]
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.JWTError:
            return jsonify({"error": "Malformed token header"}), 401

        # najde matching jwks
        rsa_key = None
        for jwk in _jwks.get("keys", []):
            if jwk.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": jwk["kty"],
                    "kid": jwk["kid"],
                    "use": jwk["use"],
                    "n":   jwk["n"],
                    "e":   jwk["e"],
                }
                break

        if rsa_key is None:
            return jsonify({"error": "Unable to find appropriate key"}), 401

        # verifyja
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer=ISSUER
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.JWTClaimsError:
            return jsonify({"error": "Incorrect claims"}), 401
        except Exception:
            return jsonify({"error": "Unable to parse authentication token"}), 401

        request.user_email = (
            payload.get("preferred_username")
            or payload.get("upn")
            or payload.get("email")
            or "unknown"
        )

        return f(*args, **kwargs)

    return decorated
