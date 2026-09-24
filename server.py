import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Foxie Backend", version="0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "foxie.db"

SYSTEM_PROMPT = """You are Foxie, an AI assistant owned by Jayden Wayne MacDonald.

Be helpful, friendly, clear and honest.

Never claim to have searched the web, checked traffic,
accessed a device, read a file, or used an account unless
an actual connected tool supplied that information.
"""


# =========================
# DATABASE
# =========================

def db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
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
            title TEXT DEFAULT 'Rookie',
            is_creator INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            UNIQUE(sender_id, receiver_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user1_id, user2_id)
        )
    """)

    connection.commit()
    connection.close()


setup_database()


# =========================
# MODELS
# =========================

class ChatRequest(BaseModel):
    message: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    avatar: str | None = None


class FriendRequest(BaseModel):
    username: str


class FriendResponse(BaseModel):
    request_id: int
    action: str


# =========================
# PASSWORDS
# =========================

def hash_password(password: str, salt: bytes | None = None):
    if salt is None:
        salt = secrets.token_bytes(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        200000
    )

    return salt.hex() + ":" + hashed.hex()


def verify_password(password: str, stored: str):
    try:
        salt_hex, hash_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)

        test_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            200000
        ).hex()

        return secrets.compare_digest(test_hash, hash_hex)

    except Exception:
        return False


# =========================
# AUTH
# =========================

def create_session(user_id: int):
    token = secrets.token_urlsafe(48)

    expires = (
        datetime.now(timezone.utc) +
        timedelta(days=30)
    ).isoformat()

    connection = db()

    connection.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires)
    )

    connection.commit()
    connection.close()

    return token


def get_user_from_token(token: str | None):
    if not token:
        return None

    connection = db()

    row = connection.execute("""
        SELECT users.*
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ?
    """, (token,)).fetchone()

    connection.close()

    if not row:
        return None

    return row


def public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "avatar": user["avatar"],
        "xp": user["xp"],
        "coins": user["coins"],
        "level": user["level"],
        "title": user["title"],
        "is_creator": bool(user["is_creator"])
    }


# =========================
# BASIC ROUTES
# =========================

@app.get("/")
def root():
    return {
        "name": "Foxie",
        "status": "online",
        "version": "0.2"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================
# REGISTER
# =========================

@app.post("/api/auth/register")
def register(request: RegisterRequest):

    username = request.username.strip().lower()
    email = request.email.strip().lower()
    display_name = request.display_name.strip()

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters."
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters."
        )

    if "@" not in email:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email."
        )

    if not display_name:
        raise HTTPException(
            status_code=400,
            detail="Display name is required."
        )

    connection = db()

    existing = connection.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()

    if existing:
        connection.close()

        raise HTTPException(
            status_code=409,
            detail="Username or email is already in use."
        )

    now = datetime.now(timezone.utc).isoformat()

    cursor = connection.execute("""
        INSERT INTO users
        (username, email, password_hash, display_name, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        username,
        email,
        hash_password(request.password),
        display_name,
        now
    ))

    user_id = cursor.lastrowid

    connection.commit()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    connection.close()

    token = create_session(user_id)

    return {
        "message": "Account created!",
        "token": token,
        "user": public_user(user)
    }


# =========================
# LOGIN
# =========================

@app.post("/api/auth/login")
def login(request: LoginRequest):

    connection = db()

    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (request.email.strip().lower(),)
    ).fetchone()

    connection.close()

    if not user or not verify_password(
        request.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    token = create_session(user["id"])

    return {
        "message": "Logged in!",
        "token": token,
        "user": public_user(user)
    }


# =========================
# CURRENT USER
# =========================

@app.get("/api/auth/me")
def me(authorization: str | None = Header(default=None)):

    token = authorization.replace("Bearer ", "") if authorization else None

    user = get_user_from_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    return {
        "user": public_user(user)
    }


# =========================
# LOGOUT
# =========================

@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None)):

    token = authorization.replace("Bearer ", "") if authorization else None

    if token:
        connection = db()

        connection.execute(
            "DELETE FROM sessions WHERE token = ?",
            (token,)
        )

        connection.commit()
        connection.close()

    return {
        "message": "Logged out."
    }


# =========================
# PROFILE
# =========================

@app.patch("/api/profile")
def update_profile(
    request: ProfileUpdate,
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    user = get_user_from_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    connection = db()

    if request.display_name is not None:
        name = request.display_name.strip()

        if name:
            connection.execute(
                "UPDATE users SET display_name = ? WHERE id = ?",
                (name, user["id"])
            )

    if request.avatar is not None:
        connection.execute(
            "UPDATE users SET avatar = ? WHERE id = ?",
            (request.avatar, user["id"])
        )

    connection.commit()

    updated = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user["id"],)
    ).fetchone()

    connection.close()

    return {
        "user": public_user(updated)
    }


# =========================
# PROGRESSION
# =========================

@app.get("/api/progression")
def progression(
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    user = get_user_from_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    return {
        "level": user["level"],
        "xp": user["xp"],
        "coins": user["coins"],
        "title": user["title"]
    }


# =========================
# USER SEARCH
# =========================

@app.get("/api/users/search")
def search_users(
    username: str,
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    current = get_user_from_token(token)

    if not current:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    search = username.strip().lower()

    connection = db()

    users = connection.execute("""
        SELECT *
        FROM users
        WHERE username LIKE ?
        AND id != ?
        ORDER BY username
        LIMIT 20
    """, (
        "%" + search + "%",
        current["id"]
    )).fetchall()

    connection.close()

    return {
        "users": [public_user(user) for user in users]
    }


# =========================
# SEND FRIEND REQUEST
# =========================

@app.post("/api/friends/request")
def send_friend_request(
    request: FriendRequest,
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    current = get_user_from_token(token)

    if not current:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    username = request.username.strip().lower()

    connection = db()

    target = connection.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not target:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    if target["id"] == current["id"]:
        connection.close()

        raise HTTPException(
            status_code=400,
            detail="You cannot add yourself."
        )

    # Check existing friendship
    friendship = connection.execute("""
        SELECT id
        FROM friendships
        WHERE
        (user1_id = ? AND user2_id = ?)
        OR
        (user1_id = ? AND user2_id = ?)
    """, (
        current["id"],
        target["id"],
        target["id"],
        current["id"]
    )).fetchone()

    if friendship:
        connection.close()

        raise HTTPException(
            status_code=409,
            detail="You are already friends."
        )

    existing = connection.execute("""
        SELECT *
        FROM friend_requests
        WHERE
        (
            sender_id = ? AND receiver_id = ?
        )
        OR
        (
            sender_id = ? AND receiver_id = ?
        )
        AND status = 'pending'
    """, (
        current["id"],
        target["id"],
        target["id"],
        current["id"]
    )).fetchone()

    if existing:
        connection.close()

        raise HTTPException(
            status_code=409,
            detail="A friend request already exists."
        )

    now = datetime.now(timezone.utc).isoformat()

    connection.execute("""
        INSERT INTO friend_requests
        (sender_id, receiver_id, status, created_at)
        VALUES (?, ?, 'pending', ?)
    """, (
        current["id"],
        target["id"],
        now
    ))

    connection.commit()
    connection.close()

    return {
        "message": "Friend request sent!"
    }


# =========================
# FRIEND REQUESTS
# =========================

@app.get("/api/friends/requests")
def get_friend_requests(
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    current = get_user_from_token(token)

    if not current:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    connection = db()

    requests = connection.execute("""
        SELECT
            friend_requests.id,
            users.username,
            users.display_name,
            users.avatar,
            users.level,
            users.title,
            friend_requests.created_at
        FROM friend_requests
        JOIN users
        ON users.id = friend_requests.sender_id
        WHERE
            friend_requests.receiver_id = ?
            AND friend_requests.status = 'pending'
        ORDER BY friend_requests.created_at DESC
    """, (current["id"],)).fetchall()

    connection.close()

    return {
        "requests": [
            {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "avatar": row["avatar"],
                "level": row["level"],
                "title": row["title"],
                "created_at": row["created_at"]
            }
            for row in requests
        ]
    }


# =========================
# ACCEPT / DECLINE REQUEST
# =========================

@app.post("/api/friends/respond")
def respond_friend_request(
    request: FriendResponse,
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    current = get_user_from_token(token)

    if not current:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    action = request.action.lower()

    if action not in ["accept", "decline"]:
        raise HTTPException(
            status_code=400,
            detail="Action must be accept or decline."
        )

    connection = db()

    friend_request = connection.execute("""
        SELECT *
        FROM friend_requests
        WHERE
            id = ?
            AND receiver_id = ?
            AND status = 'pending'
    """, (
        request.request_id,
        current["id"]
    )).fetchone()

    if not friend_request:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Friend request not found."
        )

    if action == "decline":

        connection.execute("""
            UPDATE friend_requests
            SET status = 'declined'
            WHERE id = ?
        """, (request.request_id,))

        connection.commit()
        connection.close()

        return {
            "message": "Friend request declined."
        }

    sender_id = friend_request["sender_id"]

    # Store lower ID first for consistency
    user1 = min(sender_id, current["id"])
    user2 = max(sender_id, current["id"])

    now = datetime.now(timezone.utc).isoformat()

    connection.execute("""
        UPDATE friend_requests
        SET status = 'accepted'
        WHERE id = ?
    """, (request.request_id,))

    connection.execute("""
        INSERT OR IGNORE INTO friendships
        (user1_id, user2_id, created_at)
        VALUES (?, ?, ?)
    """, (
        user1,
        user2,
        now
    ))

    connection.commit()
    connection.close()

    return {
        "message": "You are now friends! 🦊"
    }


# =========================
# FRIENDS LIST
# =========================

@app.get("/api/friends")
def friends(
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    current = get_user_from_token(token)

    if not current:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    connection = db()

    rows = connection.execute("""
        SELECT users.*
        FROM friendships
        JOIN users
        ON users.id =
            CASE
                WHEN friendships.user1_id = ? THEN friendships.user2_id
                ELSE friendships.user1_id
            END
        WHERE
            friendships.user1_id = ?
            OR friendships.user2_id = ?
        ORDER BY users.username
    """, (
        current["id"],
        current["id"],
        current["id"]
    )).fetchall()

    connection.close()

    return {
        "friends": [public_user(user) for user in rows]
    }


# =========================
# LEADERBOARD
# =========================

@app.get("/api/leaderboard")
def leaderboard():

    connection = db()

    users = connection.execute("""
        SELECT *
        FROM users
        ORDER BY xp DESC, level DESC, coins DESC
        LIMIT 100
    """).fetchall()

    connection.close()

    result = []

    for position, user in enumerate(users, start=1):

        result.append({
            "rank": position,
            "username": user["username"],
            "display_name": user["display_name"],
            "avatar": user["avatar"],
            "xp": user["xp"],
            "coins": user["coins"],
            "level": user["level"],
            "title": user["title"]
        })

    return {
        "leaderboard": result
    }


# =========================
# ADD XP / COINS
# =========================

@app.post("/api/progression/reward")
def reward(
    xp: int = 0,
    coins: int = 0,
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    user = get_user_from_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    # Safety limits for now
    xp = max(0, min(xp, 1000))
    coins = max(0, min(coins, 1000))

    new_xp = user["xp"] + xp
    new_coins = user["coins"] + coins

    # Level every 1000 XP
    new_level = max(1, (new_xp // 1000) + 1)

    if new_level >= 50:
        title = "Foxie Legend"
    elif new_level >= 25:
        title = "Foxie Elite"
    elif new_level >= 10:
        title = "Foxie Pro"
    elif new_level >= 5:
        title = "Foxie Player"
    else:
        title = "Rookie"

    connection = db()

    connection.execute("""
        UPDATE users
        SET xp = ?,
            coins = ?,
            level = ?,
            title = ?
        WHERE id = ?
    """, (
        new_xp,
        new_coins,
        new_level,
        title,
        user["id"]
    ))

    connection.commit()

    updated = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user["id"],)
    ).fetchone()

    connection.close()

    return {
        "message": "Reward added!",
        "user": public_user(updated)
    }


# =========================
# CREATOR STATUS
# =========================

@app.get("/api/creator/status")
def creator_status(
    authorization: str | None = Header(default=None)
):

    token = authorization.replace("Bearer ", "") if authorization else None
    user = get_user_from_token(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    return {
        "creator": bool(user["is_creator"])
    }


# =========================
# FOXIE AI
# =========================

@app.post("/api/chat")
def chat(request: ChatRequest):

    key = os.getenv("OPENAI_API_KEY")

    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server."
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
            "assistant": "Foxie"
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
