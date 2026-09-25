from pathlib import Path

src = Path("/mnt/data/server.txt")
out = Path("/mnt/data/server.py")

text = src.read_text(encoding="utf-8")

old = '''# ============================================================
# BASIC ROUTES
# ============================================================
'''

new = '''# ============================================================
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
'''

if old not in text:
    raise RuntimeError("Could not find the insertion point in server.py")

# Avoid duplicating the section if this file is ever processed again.
if "def foxie_ai_chat(data: ChatRequest)" not in text:
    text = text.replace(old, new, 1)

out.write_text(text, encoding="utf-8")
print(f"Created {out}")
print(f"Lines: {len(text.splitlines())}")
