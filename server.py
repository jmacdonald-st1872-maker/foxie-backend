import os
import sqlite3
import hashlib
import secrets
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================
# FOXIE BACKEND
# ============================================================

app = FastAPI(title="Foxie Backend", version="2.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DB_PATH = os.environ.get("FOXIE_DB_PATH", "foxie.db")


# ============================================================
# DATABASE
# ============================================================

def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = db()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_creator INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foxie_ownership (
            foxie_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            acquired_at REAL NOT NULL,
            acquired_from TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foxie_progress (
            foxie_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            bond INTEGER NOT NULL DEFAULT 0,
            updated_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discoveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            foxie_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            discovered_at REAL NOT NULL,
            discovery_method TEXT
        )
    """)

    connection.commit()
    connection.close()


init_db()


# ============================================================
# FOXIE UNIVERSE
# ============================================================

FOXIE_COUNT = 1_000_000
UNKNOWN_COUNT = 1_000
UNEXISTING_COUNT = 100
ONE_OF_ONE_COUNT = 10_000
APEX_COUNT = 10


FOXIE_TYPES = [
    "fire",
    "water",
    "nature",
    "electric",
    "ice",
    "shadow",
    "cosmic",
    "cyber",
    "crystal",
    "void",
    "solar",
    "wind",
    "earth",
    "spirit",
    "prism",
    "toxic",
]


TYPE_ABILITIES = {
    "fire": "Flame Heart",
    "water": "Tidal Soul",
    "nature": "Wild Growth",
    "electric": "Voltage Soul",
    "ice": "Frost Core",
    "shadow": "Dark Step",
    "cosmic": "Star Pulse",
    "cyber": "System Override",
    "crystal": "Crystal Guard",
    "void": "Void Core",
    "solar": "Solar Charge",
    "wind": "Gale Runner",
    "earth": "Earth Guard",
    "spirit": "Spirit Bond",
    "prism": "Spectrum Shift",
    "toxic": "Toxic Pulse",
}


NAME_START = [
    "Ember",
    "Nova",
    "Shadow",
    "Frost",
    "Volt",
    "Cosmo",
    "Crystal",
    "Storm",
    "Luna",
    "Solar",
    "Echo",
    "Pixel",
    "Blaze",
    "Aero",
    "Myst",
    "Flare",
    "Glitch",
    "Thunder",
    "River",
    "Terra",
    "Spirit",
    "Prism",
    "Void",
    "Cyber",
    "Star",
    "Moon",
    "Neon",
    "Inferno",
    "Galaxy",
    "Ghost",
]


NAME_END = [
    "ly",
    "on",
    "ix",
    "ora",
    "is",
    "en",
    "yx",
    "a",
    "o",
    "ia",
    "u",
    "ex",
    "ar",
    "elle",
    "ium",
    "ox",
    "ra",
    "zen",
    "byte",
    "wing",
    "flare",
    "spark",
]


RARITIES = [
    "Common",
    "Common",
    "Common",
    "Common",
    "Uncommon",
    "Rare",
    "Epic",
    "Mythic",
    "Legendary",
]


# ============================================================
# APEX FOXIES
# ============================================================

APEX_FOXIES = {

    "APEX-01": {
        "name": "The Bounty Hunter",
        "type": "shadow",
        "ability": "Hunter's Mark",
    },

    "APEX-02": {
        "name": "Volt Reaper",
        "type": "electric",
        "ability": "Infinite Voltage",
    },

    "APEX-03": {
        "name": "Galaxy Warden",
        "type": "cosmic",
        "ability": "Galaxy Core",
    },

    "APEX-04": {
        "name": "The Void King",
        "type": "void",
        "ability": "Void Dominion",
    },

    "APEX-05": {
        "name": "Dracoflare",
        "type": "fire",
        "ability": "Inferno Core",
    },

    "APEX-06": {
        "name": "Frost Monarch",
        "type": "ice",
        "ability": "Absolute Frost",
    },

    "APEX-07": {
        "name": "Nightmare",
        "type": "shadow",
        "ability": "Nightmare Realm",
    },

    "APEX-08": {
        "name": "Crystal Overlord",
        "type": "crystal",
        "ability": "Perfect Crystal",
    },

    "APEX-09": {
        "name": "Reality Breaker",
        "type": "cyber",
        "ability": "Reality Glitch",
    },

    "APEX-10": {
        "name": "The Forgotten",
        "type": "spirit",
        "ability": "Forgotten Power",
    },
}


# ============================================================
# DETERMINISTIC FOXIE GENERATION
# ============================================================

def hash_number(value: str, salt: str = "") -> int:

    raw = f"FOXIE::{salt}::{value}".encode()

    digest = hashlib.sha256(raw).hexdigest()

    return int(digest[:16], 16)


def generated_name(index: int) -> str:

    start = NAME_START[
        index % len(NAME_START)
    ]

    end = NAME_END[
        (index // len(NAME_START)) % len(NAME_END)
    ]

    return start + end


def normal_foxie(index: int):

    foxie_id = (
        f"FOX-{index:06d}"
    )

    seed = hash_number(foxie_id)

    foxie_type = FOXIE_TYPES[
        seed % len(FOXIE_TYPES)
    ]

    rarity = RARITIES[
        (seed // 17) % len(RARITIES)
    ]

    level = 1 + ((seed // 101) % 120)

    hp = 80 + ((seed // 7) % 120)

    attack = 10 + ((seed // 11) % 90)

    defense = 10 + ((seed // 13) % 90)

    speed = 10 + ((seed // 19) % 90)

    body_styles = [
        "four-legged",
        "upright",
        "mixed",
    ]

    body = body_styles[
        (seed // 23) % len(body_styles)
    ]

    evolution = evolution_for_level(level)

    return {
        "id": foxie_id,
        "name": generated_name(index),
        "type": foxie_type,
        "rarity": rarity,
        "level": level,
        "xp": max(0, (level - 1) * 100),
        "body_style": body,
        "ability": TYPE_ABILITIES[foxie_type],
        "hp": hp,
        "attack": attack,
        "defense": defense,
        "speed": speed,
        "evolution": evolution,
        "discovered": False,
        "owned": False,
        "special": False,
    }


# ============================================================
# EVOLUTION
# ============================================================

def evolution_for_level(level: int):

    if level >= 999:
        return "Final Form"

    if level >= 500:
        return "Evolution 4"

    if level >= 100:
        return "Evolution 3"

    if level >= 50:
        return "Evolution 2"

    if level >= 25:
        return "Evolution 1"

    return "Base Form"


# ============================================================
# FOXIE ID VALIDATION
# ============================================================

def valid_normal_id(index: int) -> bool:
    return 1 <= index <= FOXIE_COUNT


def get_foxie(foxie_id: str):

    foxie_id = foxie_id.upper().strip()

    # -------------------------
    # NORMAL FOXIES
    # -------------------------

    if foxie_id.startswith("FOX-"):

        try:
            number = int(
                foxie_id.split("-")[1]
            )
        except ValueError:
            return None

        if not valid_normal_id(number):
            return None

        return normal_foxie(number)


    # -------------------------
    # APEX
    # -------------------------

    if foxie_id in APEX_FOXIES:

        data = APEX_FOXIES[foxie_id]

        return {
            "id": foxie_id,
            "name": data["name"],
            "type": data["type"],
            "rarity": "Apex",
            "level": 999,
            "xp": 99800,
            "body_style": "upright",
            "ability": data["ability"],
            "hp": 999,
            "attack": 999,
            "defense": 999,
            "speed": 999,
            "evolution": "Apex Final Form",
            "discovered": False,
            "owned": False,
            "special": True,
        }


    # -------------------------
    # UNKNOWN
    # -------------------------

    if foxie_id.startswith("UNK-"):

        try:
            number = int(
                foxie_id.split("-")[1]
            )
        except ValueError:
            return None

        if not 1 <= number <= UNKNOWN_COUNT:
            return None

        return {
            "id": foxie_id,
            "name": "???",
            "type": "unknown",
            "rarity": "Unknown",
            "level": None,
            "xp": None,
            "body_style": None,
            "ability": "???",
            "hp": None,
            "attack": None,
            "defense": None,
            "speed": None,
            "evolution": "???",
            "discovered": False,
            "owned": False,
            "special": True,
        }


    # -------------------------
    # UNEXISTING
    # -------------------------

    if foxie_id.startswith("UOX-"):

        try:
            number = int(
                foxie_id.split("-")[1]
            )
        except ValueError:
            return None

        if not 1 <= number <= UNEXISTING_COUNT:
            return None

        return {
            "id": foxie_id,
            "name": "???",
            "type": "unknown",
            "rarity": "Unexisting",
            "level": None,
            "xp": None,
            "body_style": None,
            "ability": "???",
            "hp": None,
            "attack": None,
            "defense": None,
            "speed": None,
            "evolution": "???",
            "discovered": False,
            "owned": False,
            "special": True,
        }


    # -------------------------
    # ONE OF ONE
    # -------------------------

    if foxie_id.startswith("OOO-"):

        try:
            number = int(
                foxie_id.split("-")[1]
            )
        except ValueError:
            return None

        if not 1 <= number <= ONE_OF_ONE_COUNT:
            return None

        return {
            "id": foxie_id,
            "name": "???",
            "type": "unknown",
            "rarity": "One-of-One",
            "level": None,
            "xp": None,
            "body_style": None,
            "ability": "???",
            "hp": None,
            "attack": None,
            "defense": None,
            "speed": None,
            "evolution": "???",
            "discovered": False,
            "owned": False,
            "special": True,
        }


    return None


# ============================================================
# AUTH
# ============================================================

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def password_hash(password: str):

    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        200_000,
    )

    return (
        salt.hex()
        + ":"
        + digest.hex()
    )


def check_password(
    password: str,
    stored: str
):

    try:

        salt_hex, digest_hex = stored.split(":")

        salt = bytes.fromhex(salt_hex)

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            200_000,
        )

        return secrets.compare_digest(
            digest.hex(),
            digest_hex,
        )

    except Exception:

        return False


def get_current_user(
    authorization: Optional[str]
):

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization",
        )

    token = authorization[7:]

    connection = db()

    row = connection.execute(
        """
        SELECT users.*
        FROM sessions
        JOIN users
        ON users.id = sessions.user_id
        WHERE sessions.token=?
        """,
        (token,),
    ).fetchone()

    connection.close()

    if not row:

        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    return row


# ============================================================
# FOXIE AI — CHAT + BRACKEN EASTER EGG
# ============================================================

class ChatRequest(BaseModel):
    message: str


class BrackenRequest(BaseModel):
    message: str


def foxie_ai_reply(message: str) -> str:
    """
    Main Foxie AI response function.

    Bracken is a hidden Foxie easter egg.
    Other messages currently receive a basic response
    until the real AI model is connected.
    """

    message = message.strip()
    lower_message = message.lower()

    # BRACKEN EASTER EGG 🦊
    if "bracken" in lower_message:
        return "WHAT'S CRACKING BRACKING 😭🦊"

    if not message:
        return "Yo! 🦊 Send me something!"

    if lower_message in {"hi", "hello", "hey", "yo", "hiya"}:
        return "Yooo! 🦊🔥 What's up?"

    if "who are you" in lower_message:
        return "I'm Foxie AI 🦊 — the AI behind the Foxie universe."

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

    return "I'm Foxie AI 🦊 I got your message: " + message


# ============================================================
# MAIN FOXIE AI CHAT
# ============================================================

@app.post("/chat")
def foxie_ai_chat(data: ChatRequest):
    return {
        "ok": True,
        "reply": foxie_ai_reply(data.message),
    }


# ============================================================
# DIRECT BRACKEN EASTER EGG TEST
# ============================================================

@app.post("/api/ai/bracken")
def bracken_easter_egg(data: BrackenRequest):

    message = data.message.strip().lower()

    if "bracken" in message:
        return {
            "ok": True,
            "triggered": True,
            "reply": "WHAT'S CRACKING BRACKING 😭🦊",
        }

    return {
        "ok": True,
        "triggered": False,
        "reply": None,
    }


# ============================================================
# BASIC ROUTES
# ============================================================

@app.get("/")
def root():

    return {
        "name": "Foxie Backend",
        "status": "online",
        "version": "2.0",
        "foxie_universe": FOXIE_COUNT,
    }


@app.get("/health")
def health():

    return {
        "ok": True,
        "service": "foxie-backend",
    }


# ============================================================
# REGISTER
# ============================================================

@app.post("/api/auth/register")
def register(data: RegisterRequest):

    username = data.username.strip()

    if len(username) < 2:
        raise HTTPException(
            status_code=400,
            detail="Username is too short",
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password is too short",
        )

    connection = db()

    try:

        cursor = connection.execute(
            """
            INSERT INTO users
            (username,password_hash,is_creator,created_at)
            VALUES (?,?,0,?)
            """,
            (
                username,
                password_hash(data.password),
                time.time(),
            ),
        )

        connection.commit()

        user_id = cursor.lastrowid

    except sqlite3.IntegrityError:

        connection.close()

        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )

    connection.close()

    return {
        "ok": True,
        "user_id": user_id,
        "username": username,
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/auth/login")
def login(data: LoginRequest):

    connection = db()

    row = connection.execute(
        """
        SELECT *
        FROM users
        WHERE username=?
        """,
        (data.username.strip(),),
    ).fetchone()

    if not row:

        connection.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if not check_password(
        data.password,
        row["password_hash"],
    ):

        connection.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = secrets.token_urlsafe(48)

    connection.execute(
        """
        INSERT INTO sessions
        (token,user_id,created_at)
        VALUES (?,?,?)
        """,
        (
            token,
            row["id"],
            time.time(),
        ),
    )

    connection.commit()
    connection.close()

    return {
        "ok": True,
        "token": token,
        "user": {
            "id": row["id"],
            "username": row["username"],
            "is_creator": bool(row["is_creator"]),
        },
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/auth/me")
def me(
    authorization: Optional[str] = Header(None)
):

    user = get_current_user(
        authorization
    )

    return {
        "id": user["id"],
        "username": user["username"],
        "is_creator": bool(
            user["is_creator"]
        ),
    }


# ============================================================
# FOXIE DATA
# ============================================================

@app.get("/api/foxies/{foxie_id}")
def foxie_details(foxie_id: str):

    foxie = get_foxie(foxie_id)

    if not foxie:

        raise HTTPException(
            status_code=404,
            detail="Foxie not found",
        )

    return foxie


# ============================================================
# FOXIE SEARCH
# ============================================================

@app.get("/api/foxies")
def foxie_search(
    search: str = "",
    foxie_type: str = "",
    rarity: str = "",
    limit: int = 50,
):

    limit = max(
        1,
        min(limit, 100),
    )

    results = []

    search = search.strip().lower()

    # We intentionally generate only the
    # requested page instead of loading
    # one million objects into memory.

    if search.startswith("fox-"):

        try:

            number = int(
                search.replace(
                    "fox-",
                    "",
                )
            )

            foxie = get_foxie(
                f"FOX-{number:06d}"
            )

            if foxie:
                results.append(foxie)

        except ValueError:

            pass

    else:

        for number in range(
            1,
            min(
                FOXIE_COUNT,
                limit * 5,
            ) + 1,
        ):

            foxie = normal_foxie(
                number
            )

            if search:

                if search not in (
                    foxie["name"].lower()
                    + " "
                    + foxie["id"].lower()
                ):
                    continue

            if foxie_type:

                if foxie["type"] != foxie_type:
                    continue

            if rarity:

                if foxie["rarity"] != rarity:
                    continue

            results.append(foxie)

            if len(results) >= limit:
                break

    return {
        "count": len(results),
        "results": results,
    }


# ============================================================
# CLAIM / OWNERSHIP
# ============================================================

@app.post("/api/foxies/{foxie_id}/claim")
def claim_foxie(
    foxie_id: str,
    authorization: Optional[str] = Header(None),
):

    user = get_current_user(
        authorization
    )

    foxie = get_foxie(foxie_id)

    if not foxie:

        raise HTTPException(
            status_code=404,
            detail="Foxie not found",
        )

    connection = db()

    existing = connection.execute(
        """
        SELECT *
        FROM foxie_ownership
        WHERE foxie_id=?
        """,
        (foxie["id"],),
    ).fetchone()

    if existing:

        connection.close()

        raise HTTPException(
            status_code=409,
            detail="This Foxie is already owned",
        )

    # Special Foxies require the future
    # discovery/catch system.
    if foxie["special"]:

        connection.close()

        raise HTTPException(
            status_code=403,
            detail="Special Foxies must be discovered first",
        )

    now = time.time()

    connection.execute(
        """
        INSERT INTO foxie_ownership
        (foxie_id,user_id,acquired_at,acquired_from)
        VALUES (?,?,?,?)
        """,
        (
            foxie["id"],
            user["id"],
            now,
            "wild",
        ),
    )

    connection.execute(
        """
        INSERT INTO foxie_progress
        (foxie_id,user_id,xp,level,bond,updated_at)
        VALUES (?,?,?,?,?,?)
        """,
        (
            foxie["id"],
            user["id"],
            0,
            1,
            0,
            now,
        ),
    )

    connection.commit()
    connection.close()

    return {
        "ok": True,
        "foxie": foxie["id"],
        "owner_id": user["id"],
    }


# ============================================================
# MY FOXIES
# ============================================================

@app.get("/api/my-foxies")
def my_foxies(
    authorization: Optional[str] = Header(None),
):

    user = get_current_user(
        authorization
    )

    connection = db()

    rows = connection.execute(
        """
        SELECT
            o.foxie_id,
            p.xp,
            p.level,
            p.bond
        FROM foxie_ownership o
        LEFT JOIN foxie_progress p
        ON p.foxie_id=o.foxie_id
        WHERE o.user_id=?
        ORDER BY o.acquired_at DESC
        """,
        (user["id"],),
    ).fetchall()

    connection.close()

    result = []

    for row in rows:

        foxie = get_foxie(
            row["foxie_id"]
        )

        if not foxie:
            continue

        foxie["owned"] = True
        foxie["discovered"] = True

        if row["xp"] is not None:
            foxie["xp"] = row["xp"]

        if row["level"] is not None:
            foxie["level"] = row["level"]

        foxie["bond"] = (
            row["bond"] or 0
        )

        foxie["evolution"] = \
            evolution_for_level(
                foxie["level"]
            )

        result.append(foxie)

    return {
        "count": len(result),
        "foxies": result,
    }


# ============================================================
# FOXIE XP
# ============================================================

class XPRequest(BaseModel):
    amount: int


@app.post("/api/foxies/{foxie_id}/xp")
def add_foxie_xp(
    foxie_id: str,
    data: XPRequest,
    authorization: Optional[str] = Header(None),
):

    user = get_current_user(
        authorization
    )

    if data.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="XP must be positive",
        )

    connection = db()

    ownership = connection.execute(
        """
        SELECT *
        FROM foxie_ownership
        WHERE foxie_id=? AND user_id=?
        """,
        (
            foxie_id,
            user["id"],
        ),
    ).fetchone()

    if not ownership:

        connection.close()

        raise HTTPException(
            status_code=403,
            detail="You do not own this Foxie",
        )

    progress = connection.execute(
        """
        SELECT *
        FROM foxie_progress
        WHERE foxie_id=? AND user_id=?
        """,
        (
            foxie_id,
            user["id"],
        ),
    ).fetchone()

    if not progress:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Foxie progress not found",
        )

    new_xp = (
        progress["xp"]
        + data.amount
    )

    new_level = min(
        999,
        (new_xp // 100) + 1,
    )

    connection.execute(
        """
        UPDATE foxie_progress
        SET xp=?,level=?,updated_at=?
        WHERE foxie_id=? AND user_id=?
        """,
        (
            new_xp,
            new_level,
            time.time(),
            foxie_id,
            user["id"],
        ),
    )

    connection.commit()
    connection.close()

    return {
        "ok": True,
        "foxie_id": foxie_id,
        "xp": new_xp,
        "level": new_level,
        "evolution":
            evolution_for_level(
                new_level
            ),
    }


# ============================================================
# DISCOVERY
# ============================================================

class DiscoveryRequest(BaseModel):
    method: str = "exploration"


@app.post("/api/foxies/{foxie_id}/discover")
def discover_foxie(
    foxie_id: str,
    data: DiscoveryRequest,
    authorization: Optional[str] = Header(None),
):

    user = get_current_user(
        authorization
    )

    foxie = get_foxie(foxie_id)

    if not foxie:

        raise HTTPException(
            status_code=404,
            detail="Foxie not found",
        )

    connection = db()

    existing = connection.execute(
        """
        SELECT *
        FROM discoveries
        WHERE foxie_id=?
        """,
        (foxie_id,),
    ).fetchone()

    if existing:

        connection.close()

        return {
            "ok": True,
            "already_discovered": True,
            "foxie": foxie,
        }

    now = time.time()

    connection.execute(
        """
        INSERT INTO discoveries
        (foxie_id,user_id,discovered_at,discovery_method)
        VALUES (?,?,?,?)
        """,
        (
            foxie_id,
            user["id"],
            now,
            data.method,
        ),
    )

    connection.commit()
    connection.close()

    foxie["discovered"] = True

    return {
        "ok": True,
        "first_discoverer": user["id"],
        "foxie": foxie,
    }


# ============================================================
# UNIVERSE STATS
# ============================================================

@app.get("/api/foxie-universe")
def foxie_universe():

    return {

        "normal_foxies": FOXIE_COUNT,

        "unknown": UNKNOWN_COUNT,

        "unexisting": UNEXISTING_COUNT,

        "one_of_one": ONE_OF_ONE_COUNT,

        "apex": APEX_COUNT,

        "total_special_slots":
            UNKNOWN_COUNT
            + UNEXISTING_COUNT
            + ONE_OF_ONE_COUNT
            + APEX_COUNT,

        "evolution_levels":[
            25,
            50,
            100,
            500,
            999,
        ],

        "spawn_schedule":{

            "apex":
                "1 per month",

            "unexisting":
                "1 per week",

            "unknown":
                "daily",

            "one_of_one":
                "daily",
        },

    }
