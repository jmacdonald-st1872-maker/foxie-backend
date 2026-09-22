import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Foxie Backend", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your Foxie domain after deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are Foxie, an AI assistant owned by JJ.
Be helpful, clear, and honest about your capabilities.
Never claim to have searched the web, checked traffic, accessed a device,
read a file, or used an account unless an actual connected tool supplied
that information.
Respect the permissions configured by JJ.
"""

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"name": "Foxie", "owner": "JJ", "status": "online"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(request: ChatRequest):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server."
        )

    client = OpenAI(api_key=key)

       try:
        response = client.responses.create(
            model="gpt-5.6",
            instructions=SYSTEM_PROMPT,
            input=request.message,
        )
    except Exception as e:
        print(f"OPENAI ERROR: {type(e).__name__}: {e}", flush=True)
        raise HTTPException(status_code=500, detail="OpenAI request failed")
    return {
        "reply": response.output_text,
        "assistant": "Foxie",
        "owner": "JJ"
    }
