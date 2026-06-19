from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse
import anthropic
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Serve images publicly via /images
app.mount("/images", StaticFiles(directory="temp"), name="images")

# Load memory from file
MEMORY_FILE = "memory.json"

def load_memory():
    if Path(MEMORY_FILE).exists():
        return json.loads(Path(MEMORY_FILE).read_text())
    return {"preferences": [], "conversation_history": []}

def save_memory(memory):
    Path(MEMORY_FILE).write_text(json.dumps(memory, indent=2))

memory = load_memory()

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

NGROK_URL = os.getenv("NGROK_URL")  # e.g. https://armhole-commence-distaste.ngrok-free.dev

SYSTEM_PROMPT = """You are a wildlife camera assistant. You help the user monitor wildlife spotted by their camera.

You have memory of the user's preferences about which animals they are interested in or not interested in.

Current user preferences:
{preferences}

When the user tells you they are or aren't interested in certain animals, acknowledge it and I will store it in memory.

If the user asks to see the latest picture, let them know you're sending it.

Respond concisely and in a friendly manner."""

@app.post("/webhook/whatsapp")
async def whatsapp_reply(request: Request):
    """Handle incoming WhatsApp messages from the user."""
    form_data = await request.form()
    body = form_data.get("Body", "")
    from_number = form_data.get("From", "")

    print(f"Received from {from_number}: {body}")

    memory["conversation_history"].append({"role": "user", "content": body})

    # Build system prompt with preferences
    prefs = "\n".join(memory["preferences"]) if memory["preferences"] else "None yet."
    system = SYSTEM_PROMPT.format(preferences=prefs)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=memory["conversation_history"],
    )

    assistant_message = response.content[0].text
    memory["conversation_history"].append({"role": "assistant", "content": assistant_message})

    # Check if user is setting preferences
    _update_preferences(body, assistant_message)

    save_memory(memory)

    print(f"Replying: {assistant_message}")

    # Reply via Twilio
    twiml = MessagingResponse()
    msg = twiml.message(assistant_message)

    # Send latest picture if user asks for it
    if _wants_picture(body):
        for filename in ["picture.jpg", "image.png", "sample_wildlife.jpg"]:
            image_path = Path(f"temp/{filename}")
            if image_path.exists() and NGROK_URL:
                # Add timestamp to bust Twilio's cache
                msg.media(f"{NGROK_URL}/images/{filename}?t={int(os.path.getmtime(image_path))}")
                break

    return Response(content=str(twiml), media_type="application/xml")


def _wants_picture(body: str) -> bool:
    """Check if user is asking for a picture."""
    keywords = ["picture", "photo", "image", "show me", "send pic", "what did you see"]
    return any(k in body.lower() for k in keywords)


def _update_preferences(user_msg: str, assistant_reply: str):
    """Use Claude to extract preference updates."""
    extraction = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system="Extract any animal preference from the user message. Return ONLY a JSON object like: {\"action\": \"add\" or \"remove\", \"preference\": \"interested in foxes\"} or {\"action\": \"none\"} if no preference was stated.",
        messages=[{"role": "user", "content": user_msg}],
    )

    try:
        result = json.loads(extraction.content[0].text)
        if result.get("action") == "add":
            memory["preferences"].append(result["preference"])
        elif result.get("action") == "remove":
            memory["preferences"] = [p for p in memory["preferences"] if result["preference"].lower() not in p.lower()]
    except (json.JSONDecodeError, KeyError):
        pass