import os
import sqlite3
import hashlib
import secrets
import hmac
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Foxie Backend", version="0.2")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE
# =========================================================

DB_FILE = os.getenv("FOXIE_DB", "foxie.db")


def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            avatar TEXT DEFAULT '🦊',
            xp INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            title TEXT DEFAULT 'Foxie Member',
            is_creator INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


setup_database()


# =========================================================
# PASSWORD SECURITY
# =========================================================

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000
    )

    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, hash_hex = stored_hash.split(":")

        salt = bytes.fromhex(salt_hex)

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            200_000
        )

        return hmac.compare_digest(
            calculated.hex(),
            hash_hex
        )

    except Exception:
        return False


# =========================================================
# SESSIONS
# =========================================================

SESSION_DAYS = 30


def create_session(user_id: int):
    token = secrets.token_urlsafe(48)

    expires = datetime.now(timezone.utc) + timedelta(
        days=SESSION_DAYS
    )

    db = get_db()

    db.execute(
        """
        INSERT INTO sessions (token, user_id, expires_at)
        VALUES (?, ?, ?)
        """,
        (
            token,
            user_id,
            expires.isoformat()
        )
    )

    db.commit()
    db.close()

    return token


def get_current_user(authorization: str | None):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )

    token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing session token."
        )

    db = get_db()

    row = db.execute(
        """
        SELECT
            users.*,
            sessions.expires_at
        FROM sessions
        JOIN users
            ON users.id = sessions.user_id
        WHERE sessions.token = ?
        """,
        (token,)
    ).fetchone()

    db.close()

    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid session."
        )

    expires = datetime.fromisoformat(row["expires_at"])

    if expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=401,
            detail="Session expired."
        )

    return row


# =========================================================
# FOXIE AI
# =========================================================

SYSTEM_PROMPT = """You are Foxie, an AI assistant owned by JJ.

Be helpful, clear, and honest about your capabilities.

Never claim to have searched the web, checked traffic, accessed a device,
read a file, or used an account unless an actual connected tool supplied
that information.

Respect the permissions configured by JJ.
"""


class ChatRequest(BaseModel):
    message: str


# =========================================================
# ACCOUNT MODELS
# =========================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    avatar: str | None = None


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
def root():
    return {
        "name": "Foxie",
        "owner": "JJ",
        "status": "online",
        "version": "0.2"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================================================
# REGISTER
# =========================================================

@app.post("/api/auth/register")
def register(request: RegisterRequest):

    username = request.username.strip()
    email = request.email.strip().lower()
    display_name = request.display_name.strip()

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters."
        )

    if len(password := request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters."
        )

    if not email or "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email."
        )

    if not display_name:
        raise HTTPException(
            status_code=400,
            detail="Display name is required."
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = ? OR email = ?
        """,
        (username, email)
    ).fetchone()

    if existing:
        db.close()

        raise HTTPException(
            status_code=409,
            detail="Username or email already exists."
        )

    password_hash = hash_password(password)

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    cursor = db.execute(
        """
        INSERT INTO users (
            username,
            email,
            password_hash,
            display_name,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            username,
            email,
            password_hash,
            display_name,
            created_at
        )
    )

    user_id = cursor.lastrowid

    db.commit()
    db.close()

    token = create_session(user_id)

    return {
        "message": "Account created.",
        "token": token,
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "display_name": display_name,
            "avatar": "🦊",
            "xp": 0,
            "coins": 0,
            "level": 1,
            "title": "Foxie Member",
            "is_creator": False
        }
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/auth/login")
def login(request: LoginRequest):

    email = request.email.strip().lower()

    db = get_db()

    user = db.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    db.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not verify_password(
        request.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    token = create_session(user["id"])

    return {
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "display_name": user["display_name"],
            "avatar": user["avatar"],
            "xp": user["xp"],
            "coins": user["coins"],
            "level": user["level"],
            "title": user["title"],
            "is_creator": bool(user["is_creator"])
        }
    }


# =========================================================
# CURRENT USER
# =========================================================

@app.get("/api/auth/me")
def me(
    authorization: str | None = Header(default=None)
):

    user = get_current_user(authorization)

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "display_name": user["display_name"],
        "avatar": user["avatar"],
        "xp": user["xp"],
        "coins": user["coins"],
        "level": user["level"],
        "title": user["title"],
        "is_creator": bool(user["is_creator"]),
        "created_at": user["created_at"]
    }


# =========================================================
# LOGOUT
# =========================================================

@app.post("/api/auth/logout")
def logout(
    authorization: str | None = Header(default=None)
):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    token = authorization[7:].strip()

    db = get_db()

    db.execute(
        "DELETE FROM sessions WHERE token = ?",
        (token,)
    )

    db.commit()
    db.close()

    return {
        "message": "Logged out."
    }


# =========================================================
# PROFILE
# =========================================================

@app.patch("/api/profile")
def update_profile(
    request: ProfileUpdateRequest,
    authorization: str | None = Header(default=None)
):

    user = get_current_user(authorization)

    new_display_name = request.display_name
    new_avatar = request.avatar

    if new_display_name is not None:
        new_display_name = new_display_name.strip()

        if not new_display_name:
            raise HTTPException(
                status_code=400,
                detail="Display name cannot be empty."
            )

    db = get_db()

    if new_display_name is not None and new_avatar is not None:

        db.execute(
            """
            UPDATE users
            SET display_name = ?, avatar = ?
            WHERE id = ?
            """,
            (
                new_display_name,
                new_avatar,
                user["id"]
            )
        )

    elif new_display_name is not None:

        db.execute(
            """
            UPDATE users
            SET display_name = ?
            WHERE id = ?
            """,
            (
                new_display_name,
                user["id"]
            )
        )

    elif new_avatar is not None:

        db.execute(
            """
            UPDATE users
            SET avatar = ?
            WHERE id = ?
            """,
            (
                new_avatar,
                user["id"]
            )
        )

    db.commit()

    updated = db.execute(
        """
        SELECT
            id,
            username,
            email,
            display_name,
            avatar,
            xp,
            coins,
            level,
            title,
            is_creator
        FROM users
        WHERE id = ?
        """,
        (user["id"],)
    ).fetchone()

    db.close()

    return {
        "message": "Profile updated.",
        "user": {
            "id": updated["id"],
            "username": updated["username"],
            "email": updated["email"],
            "display_name": updated["display_name"],
            "avatar": updated["avatar"],
            "xp": updated["xp"],
            "coins": updated["coins"],
            "level": updated["level"],
            "title": updated["title"],
            "is_creator": bool(updated["is_creator"])
        }
    }


# =========================================================
# XP + COINS
# =========================================================

@app.get("/api/progression")
def progression(
    authorization: str | None = Header(default=None)
):

    user = get_current_user(authorization)

    return {
        "xp": user["xp"],
        "coins": user["coins"],
        "level": user["level"],
        "title": user["title"]
    }


# =========================================================
# AI CHAT
# =========================================================

@app.post("/api/chat")
def chat(request: ChatRequest):

    key = os.getenv("OPENAI_API_KEY")

    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server."
        )

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    try:

        client = OpenAI(api_key=key)

        response = client.responses.create(
            model="gpt-5.6",
            instructions=SYSTEM_PROMPT,
            input=request.message,
        )

        return {
            "reply": response.output_text,
            "assistant": "Foxie",
            "owner": "JJ"
        }

    except Exception as e:

        print(
            f"OPENAI ERROR: {type(e).__name__}: {e}",
            flush=True
        )

        raise HTTPException(
            status_code=502,
            detail=f"OpenAI request failed: {type(e).__name__}: {e}"
        )


# =========================================================
# CREATOR MODE FOUNDATION
# =========================================================

@app.get("/api/creator/status")
def creator_status(
    authorization: str | None = Header(default=None)
):

    user = get_current_user(authorization)

    return {
        "creator_mode": bool(user["is_creator"]),
        "user_id": user["id"]
    }
