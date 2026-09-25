from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import hashlib
import secrets
import hmac
import random
from typing import Optional

app = FastAPI(
    title="Foxie Backend",
    version="2.0"
)

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

DB_PATH = os.getenv("FOXIE_DB_PATH", "foxie.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS foxie_ownership (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            foxie_id INTEGER NOT NULL,
            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS foxie_progress (
            user_id INTEGER NOT NULL,
            foxie_id INTEGER NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, foxie_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS discoveries (
            user_id INTEGER NOT NULL,
            foxie_id INTEGER NOT NULL,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, foxie_id)
        )
    """)

    conn.commit()
    conn.close()


init_db()

# =========================================================
# FOXIE UNIVERSE
# =========================================================

NORMAL_FOXIES = 1_000_000
UNKNOWN_FOXIES = 1_000
UNEXISTING_FOXIES = 100
ONE_OF_ONE_FOXIES = 10_000
APEX_FOXIES = 10

FOXIE_TYPES = [
    "Fire",
    "Water",
    "Earth",
    "Air",
    "Electric",
    "Ice",
    "Shadow",
    "Light",
    "Nature",
    "Metal",
    "Psychic",
    "Cosmic",
    "Crystal",
    "Toxic",
    "Mystic",
    "Void",
]

TYPE_ABILITIES = {
    "Fire": "Flame Burst",
    "Water": "Tidal Rush",
    "Earth": "Ground Slam",
    "Air": "Sky Dash",
    "Electric": "Thunder Strike",
    "Ice": "Frost Freeze",
    "Shadow": "Dark Pulse",
    "Light": "Radiant Beam",
    "Nature": "Vine Trap",
    "Metal": "Steel Crash",
    "Psychic": "Mind Wave",
    "Cosmic": "Star Burst",
    "Crystal": "Crystal Shield",
    "Toxic": "Venom Blast",
    "Mystic": "Mystic Force",
    "Void": "Void Collapse",
}

RARITIES = [
    "Common",
    "Uncommon",
    "Rare",
    "Epic",
    "Legendary",
    "Mythic",
    "Apex",
]

# =========================================================
# FOXIE GENERATION
# =========================================================

def generate_foxie(foxie_id: int):
    random.seed(foxie_id)

    foxie_type = random.choice(FOXIE_TYPES)

    roll = random.random()

    if foxie_id <= APEX_FOXIES:
        rarity = "Apex"
    elif roll < 0.45:
        rarity = "Common"
    elif roll < 0.70:
        rarity = "Uncommon"
    elif roll < 0.87:
        rarity = "Rare"
    elif roll < 0.95:
        rarity = "Epic"
    elif roll < 0.99:
        rarity = "Legendary"
    else:
        rarity = "Mythic"

    name_prefixes = [
        "Flame",
        "Shadow",
        "Crystal",
        "Storm",
        "Night",
        "Solar",
        "Lunar",
        "Wild",
        "Mystic",
        "Cyber",
        "Frost",
        "Thunder",
    ]

    name_suffixes = [
        "Fox",
        "Fang",
        "Tail",
        "Runner",
        "Spirit",
        "Claw",
        "Dash",
        "Howl",
        "Spark",
        "Hunter",
        "Wing",
        "Byte",
    ]

    name = (
        random.choice(name_prefixes)
        + random.choice(name_suffixes)
        + str(foxie_id)
    )

    return {
        "id": foxie_id,
        "name": name,
        "type": foxie_type,
        "ability": TYPE_ABILITIES[foxie_type],
        "rarity": rarity,
    }


# =========================================================
# APEX FOXIES
# =========================================================

def get_apex_foxies():
    return [
        generate_foxie(i)
        for i in range(1, APEX_FOXIES + 1)
    ]


# =========================================================
# EVOLUTION
# =========================================================

def get_evolution_level(xp: int):
    if xp >= 999:
        return 5
    if xp >= 500:
        return 4
    if xp >= 100:
        return 3
    if xp >= 50:
        return 2
    if xp >= 25:
        return 1

    return 0


# =========================================================
# PASSWORD SECURITY
# =========================================================

def hash_password(password: str):
    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        200_000
    )

    return salt.hex() + ":" + password_hash.hex()


def verify_password(password: str, stored_hash: str):
    try:
        salt_hex, hash_hex = stored_hash.split(":")

        salt = bytes.fromhex(salt_hex)

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            200_000
        )

        return hmac.compare_digest(
            password_hash.hex(),
            hash_hex
        )

    except Exception:
        return False


# =========================================================
# AUTH
# =========================================================

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
def register(data: RegisterRequest):

    username = data.username.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username required"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )

    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    password_hash = hash_password(data.password)

    cursor = conn.execute(
        """
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
        """,
        (username, password_hash)
    )

    user_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "user_id": user_id,
        "username": username
    }


@app.post("/api/auth/login")
def login(data: LoginRequest):

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (data.username.strip(),)
    ).fetchone()

    if not user:
        conn.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        data.password,
        user["password_hash"]
    ):
        conn.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    token = secrets.token_urlsafe(32)

    conn.execute(
        """
        INSERT INTO sessions (token, user_id)
        VALUES (?, ?)
        """,
        (token, user["id"])
    )

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "token": token,
        "user_id": user["id"],
        "username": user["username"]
    }


def get_current_user(authorization: Optional[str]):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization required"
        )

    token = authorization

    if token.startswith("Bearer "):
        token = token[7:]

    conn = get_db()

    row = conn.execute(
        """
        SELECT users.*
        FROM users
        JOIN sessions
        ON sessions.user_id = users.id
        WHERE sessions.token = ?
        """,
        (token,)
    ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )

    return row


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(None)):

    user = get_current_user(authorization)

    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
def root():
    return {
        "ok": True,
        "name": "Foxie Backend",
        "version": "2.0"
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "status": "healthy"
    }


# =========================================================
# FOXIE DATA
# =========================================================

@app.get("/api/foxie/{foxie_id}")
def foxie_details(foxie_id: int):

    if foxie_id < 1:
        raise HTTPException(
            status_code=404,
            detail="Foxie not found"
        )

    return {
        "ok": True,
        "foxie": generate_foxie(foxie_id)
    }


@app.get("/api/foxies/search")
def search_foxies(q: str = ""):

    results = []

    q = q.lower().strip()

    for foxie_id in range(1, 101):

        foxie = generate_foxie(foxie_id)

        if (
            not q
            or q in foxie["name"].lower()
            or q in foxie["type"].lower()
            or q in foxie["rarity"].lower()
        ):
            results.append(foxie)

    return {
        "ok": True,
        "results": results
    }


# =========================================================
# CLAIM FOXIE
# =========================================================

@app.post("/api/foxie/{foxie_id}/claim")
def claim_foxie(
    foxie_id: int,
    authorization: Optional[str] = Header(None)
):

    user = get_current_user(authorization)

    foxie = generate_foxie(foxie_id)

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM foxie_ownership
        WHERE user_id = ?
        AND foxie_id = ?
        """,
        (user["id"], foxie_id)
    ).fetchone()

    if existing:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="You already own this Foxie"
        )

    conn.execute(
        """
        INSERT INTO foxie_ownership
        (user_id, foxie_id)
        VALUES (?, ?)
        """,
        (user["id"], foxie_id)
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO foxie_progress
        (user_id, foxie_id, xp, level)
        VALUES (?, ?, 0, 1)
        """,
        (user["id"], foxie_id)
    )

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "foxie": foxie
    }


# =========================================================
# MY FOXIES
# =========================================================

@app.get("/api/my-foxies")
def my_foxies(
    authorization: Optional[str] = Header(None)
):

    user = get_current_user(authorization)

    conn = get_db()

    rows = conn.execute(
        """
        SELECT foxie_id
        FROM foxie_ownership
        WHERE user_id = ?
        """,
        (user["id"],)
    ).fetchall()

    conn.close()

    foxies = [
        generate_foxie(row["foxie_id"])
        for row in rows
    ]

    return {
        "ok": True,
        "foxies": foxies
    }


# =========================================================
# XP
# =========================================================

class XPRequest(BaseModel):
    foxie_id: int
    xp: int


@app.post("/api/foxie/xp")
def add_xp(
    data: XPRequest,
    authorization: Optional[str] = Header(None)
):

    user = get_current_user(authorization)

    conn = get_db()

    owned = conn.execute(
        """
        SELECT id
        FROM foxie_ownership
        WHERE user_id = ?
        AND foxie_id = ?
        """,
        (user["id"], data.foxie_id)
    ).fetchone()

    if not owned:
        conn.close()

        raise HTTPException(
            status_code=403,
            detail="You do not own this Foxie"
        )

    row = conn.execute(
        """
        SELECT xp
        FROM foxie_progress
        WHERE user_id = ?
        AND foxie_id = ?
        """,
        (user["id"], data.foxie_id)
    ).fetchone()

    current_xp = row["xp"] if row else 0

    new_xp = max(
        0,
        current_xp + data.xp
    )

    level = get_evolution_level(new_xp) + 1

    conn.execute(
        """
        INSERT OR REPLACE INTO foxie_progress
        (user_id, foxie_id, xp, level)
        VALUES (?, ?, ?, ?)
        """,
        (
            user["id"],
            data.foxie_id,
            new_xp,
            level
        )
    )

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "foxie_id": data.foxie_id,
        "xp": new_xp,
        "level": level
    }


# =========================================================
# DISCOVERIES
# =========================================================

@app.post("/api/foxie/{foxie_id}/discover")
def discover_foxie(
    foxie_id: int,
    authorization: Optional[str] = Header(None)
):

    user = get_current_user(authorization)

    conn = get_db()

    conn.execute(
        """
        INSERT OR IGNORE INTO discoveries
        (user_id, foxie_id)
        VALUES (?, ?)
        """,
        (user["id"], foxie_id)
    )

    conn.commit()
    conn.close()

    return {
        "ok": True,
        "foxie": generate_foxie(foxie_id)
    }


# =========================================================
# FOXIE UNIVERSE
# =========================================================

@app.get("/api/foxie-universe")
def foxie_universe():

    return {
        "ok": True,
        "universe": {
            "normal": NORMAL_FOXIES,
            "unknown": UNKNOWN_FOXIES,
            "unexisting": UNEXISTING_FOXIES,
            "one_of_one": ONE_OF_ONE_FOXIES,
            "apex": APEX_FOXIES,
            "total": (
                NORMAL_FOXIES
                + UNKNOWN_FOXIES
                + UNEXISTING_FOXIES
                + ONE_OF_ONE_FOXIES
                + APEX_FOXIES
            )
        },
        "types": FOXIE_TYPES,
        "apex_foxies": get_apex_foxies()
    }


# =========================================================
# FOXIE AI
# =========================================================

class ChatRequest(BaseModel):
    message: str


def foxie_ai_reply(message: str) -> str:

    message = message.strip()
    lower_message = message.lower()

    if not message:
        return "Yo! 🦊 Send me something!"

    if lower_message in {
        "hi",
        "hello",
        "hey",
        "yo",
        "hiya"
    }:
        return "Yooo! 🦊🔥 What's up?"

    if "who are you" in lower_message:
        return (
            "I'm Foxie AI 🦊 — "
            "the AI behind the Foxie universe."
        )

    if "what is foxie" in lower_message:
        return (
            "Foxie is your all-in-one world for games, "
            "Foxies, friends, tournaments, social features "
            "and way more. 🦊🌎"
        )

    if "foxie" in lower_message:
        return (
            "FOXIE 🦊🔥 We're building the whole universe "
            "one feature at a time."
        )

    return (
        "I'm Foxie AI 🦊 I got your message: "
        + message
    )


@app.post("/chat")
def foxie_ai_chat(data: ChatRequest):

    return {
        "ok": True,
        "reply": foxie_ai_reply(data.message)
    }
