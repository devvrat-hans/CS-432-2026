import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_MINS
from logger import log_unauthorized


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int, username: str, role: str) -> dict:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINS)
    payload = {
        "sub":      user_id,
        "username": username,
        "role":     role,
        "exp":      expiry,
        "iat":      datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "expiry": expiry.isoformat()}


def decode_token(token: str) -> dict:
    """Returns payload or raises jwt exceptions."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _extract_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.headers.get("X-Session-Token", "")


# ── Decorators ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            log_unauthorized(
                request.remote_addr, request.method,
                request.path, "No session token"
            )
            return jsonify({"error": "No session found"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            log_unauthorized(
                request.remote_addr, request.method,
                request.path, "Session expired"
            )
            return jsonify({"error": "Session expired"}), 401
        except jwt.InvalidTokenError:
            log_unauthorized(
                request.remote_addr, request.method,
                request.path, "Invalid session token"
            )
            return jsonify({"error": "Invalid session token"}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            log_unauthorized(
                request.remote_addr, request.method,
                request.path, "No session token"
            )
            return jsonify({"error": "No session found"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid session token"}), 401
        if payload.get("role") != "admin":
            log_unauthorized(
                request.remote_addr, request.method,
                request.path,
                f"Role '{payload.get('role')}' insufficient — admin required"
            )
            return jsonify({"error": "Admin access required"}), 403
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated
