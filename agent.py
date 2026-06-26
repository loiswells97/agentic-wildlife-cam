import anthropic
import dotenv
import base64
from pathlib import Path
import subprocess
import json
from gpiozero import MotionSensor
from gpio import play_buzzer_tune, play_rgb_led_pattern, check_motion_sensor
from twilio.rest import Client
import os
import platform

from picamzero import Camera
from datetime import datetime
import threading
from time import sleep
from classifier import classify_image

cam = Camera()

dotenv.load_dotenv()

anthropic_client = anthropic.Anthropic()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

MY_WHATSAPP = os.getenv("MY_WHATSAPP")
TWILIO_WHATSAPP = os.getenv("TWILIO_WHATSAPP")

VALID_NOTES = ["A3", "A#3" "B3", "C4", "B#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4", "C5", "C#5", "D5", "D#5", "E5", "F5", "F#5", "G5", "G#5", "A5"]
pir = MotionSensor(os.getenv("MOTION_SENSOR_PIN"))

_buzzer_lock = threading.Lock()

TOOLS = [
    # {
    #     "name": "start_video",
    #     "description": "Take a 10 second recording, returns content of video",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {},
    #         "required": []
    #     }
    # },
    # {
    #     "name": "take_picture",
    #     "description": "Take a picture, returns content of the image",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {},
    #         "required": []
    #     }
    # },
        {
        "name": "identify_animal",
        "description": "Take a photo with the camera and classify the animal using a local model. Returns the animal name and confidence score (0-1). Call again if confidence is low or the result is unknown.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "play_tune",
        "description": f"Play a tune asynchronously through the buzzer, with the tune being a list of pairs of tone names and durations in seconds. Valid notes are {', '.join(VALID_NOTES)}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tune": {
                    "type": "array",
                    "description": "Notes to play in order",
                    "items": {
                        "type": "object",
                        "properties": {
                            "note": {
                                "type": "string",
                                "description": "Note name, e.g. C4, D4, E4, F4, G4, A4, B4"
                            },
                            "duration": {
                                "type": "number",
                                "description": "How long to hold the note, in seconds"
                            }
                        },
                        "required": ["note", "duration"]
                    }
                }
            },
            "required": ["tune"]
        }
    },
    {
        "name": "show_rgb_led_pattern",
        "description": "Play a pattern of colours on an RBG LED, with the pattern composed of a list of pairs of colours and durations in seconds. Each colour is given by a tuple of numbers between 0 and 1 inclusive for red, green and blue respectively",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "array",
                    "description": "Colours to show in order with their respective durations",
                    "items": {
                        "type": "object",
                        "properties": {
                            "colour": {
                                "type": "array",
                                "description": "Colour tuple of three numbers between 0 and 1 inclusive for red, green and blue respectively e.g. [0,1,0]",
                            },
                            "duration": {
                                "type": "number",
                                "description": "How long to show the colour, in seconds"
                            }
                        },
                        "required": ["colour", "duration"]
                    }
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "check_for_motion",
        "description": "Check whether there is motion using a PIR sensor",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "send_whatsapp",
        "description": "Send a WhatsApp message to Artemis",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "write_memory",
        "description": "Append text to the memory to be loaded up next time the agent is run",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string"
                }
            },
            "required": ["text"]
        }
    }
]

def start_video():
    """Record a short clip and return sampled frames as image content blocks.

    Claude can't read video directly, so we extract ~1 frame/sec with ffmpeg
    and hand them back as a sequence of images for the model to inspect.
    """
    cam.take_video("temp/wildlife.mp4", 10)

    # Clear any frames from a previous run, then sample 1 frame per second.
    for old in Path("temp").glob("frame_*.jpg"):
        old.unlink()
    subprocess.run(
        ["ffmpeg", "-y", "-i", "temp/wildlife.mp4", "-vf", "fps=1", "temp/frame_%03d.jpg"],
        check=True,
        capture_output=True,
    )

    frames = sorted(Path("temp").glob("frame_*.jpg"))
    if not frames:
        return "Error: no frames extracted from the recording"

    blocks = [{"type": "text", "text": f"{len(frames)} frames sampled from a 10s clip, in order:"}]
    for frame in frames:
        data = base64.standard_b64encode(frame.read_bytes()).decode("utf-8")
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
        })
    return blocks

def play_tune(tune):
    for item in tune:
        if item["note"] not in VALID_NOTES:
            return f"Invalid note {item['note']}. Valid notes are in the range A3 to A5. Please try again."
    notes = [(item["note"], item["duration"]) for item in tune]
    pin = int(os.getenv("BUZZER_PIN"))

    def _play():
        with _buzzer_lock:
            play_buzzer_tune(pin, notes)

    thread = threading.Thread(target=_play, daemon=True).start()

    return "Started playing tune in background"

def show_rgb_led_pattern(pattern):
    led_pattern = [(item["colour"], item["duration"]) for item in pattern]
    play_rgb_led_pattern(os.getenv("RGB_LED_RED_PIN"), os.getenv("RGB_LED_GREEN_PIN"), os.getenv("RGB_LED_BLUE_PIN"), led_pattern)
    return "Successfully played RGB LED pattern"

def check_for_motion():
    is_motion = check_motion_sensor(pir)
    if is_motion:
        return "Motion detected"
    else:
        return "No motion detected"

def identify_animal():
    """Take a photo and return local classifier result as text for the LLM."""
    Path("temp").mkdir(exist_ok=True)
    picture_path = Path("temp/picture.jpg")

    if picture_path.exists():
        picture_path.unlink()

    cam.take_photo(str(picture_path))
    result = classify_image(str(picture_path))

    animal = result["animal"]
    confidence = result["confidence"]
    return f"animal={animal}, confidence={confidence}"

def take_picture():
    """Take a picture and return the image"""
    
    # Clear any pictures from a previous run
    for old in Path("temp").glob("picture.jpg"):
        old.unlink()

    cam.take_photo("temp/picture.jpg")

    blocks = [{"type": "text", "text": "Picture taken:"}]
    data = base64.standard_b64encode(Path("temp/picture.jpg").read_bytes()).decode("utf-8")
    blocks.append({
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
    })
    return blocks

def load_memory_json() -> dict:
    p = Path("memory.json")
    if p.exists():
        return json.loads(p.read_text())
    return {"preferences": [], "conversation_history": []}

def save_memory_json(data: dict):
    Path("memory.json").write_text(json.dumps(data, indent=2))

def send_whatsapp(message: str):
    client = Client(
        ACCOUNT_SID,
        AUTH_TOKEN
    )

    client.messages.create(
        from_=TWILIO_WHATSAPP,
        to=MY_WHATSAPP,
        body=message
    )

    # Record outbound message so the webhook server has full conversation context
    mem = load_memory_json()
    mem["conversation_history"].append({"role": "assistant", "content": message})
    save_memory_json(mem)

    return "WhatsApp message sent"

def write_memory(text):
    # Append to memory file with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("memory/wildlife_cam.md", "a") as f:
        f.write(f"{timestamp} - {text}\n")
    return "Wrote text to memory"

def run_tool(name: str, arguments: dict):
    try:
        if name == "start_video":
            return start_video()
        if name == "play_tune":
            return play_tune(arguments["tune"])
        if name == "show_rgb_led_pattern":
            return show_rgb_led_pattern(arguments["pattern"])
        if name == "check_for_motion":
            return check_for_motion()
        if name == "take_picture":
            return take_picture()
        if name == "identify_animal":
            return identify_animal()
        if name == "send_whatsapp":
            return send_whatsapp(arguments["message"])
        if name == "write_memory":
            return write_memory(arguments["text"])
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    raise ValueError(f"Unknown tool: {name}")

def agent(prompt: str, max_turns: int=10) -> str:
    messages = [{"role": "user", "content": prompt}]

    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn} ---")

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "text":
                print(f"[assistant] {block.text}")
            elif block.type == "tool_use":
                print(f"[tool call] {block.name}({block.input})")
                result = run_tool(block.name, block.input)
                is_error = isinstance(result, str) and result.startswith("Error:")
                if isinstance(result, str):
                    print(f"[tool result] {result[:200]}{'...' if len(result) > 200 else ''}")
                else:
                    print(f"[tool result] {len(result)} content blocks")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                    "is_error": is_error,
                })

        if response.stop_reason == "end_turn":
            return next(b.text for b in response.content if b.type == "text")

        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"Agent did not terminate within {max_turns} turns.")

print("Warming up the motion sensor for 30s....")
sleep(30)
print("Ready...")

while True:
    if pir.motion_detected:
        prompt = Path("prompts/wildlife_cam.md").read_text()
        sightings = Path("memory/wildlife_cam.md").read_text()
        mem = load_memory_json()
        prefs = "\n".join(mem["preferences"]) if mem["preferences"] else "None recorded yet."
        prompt_with_memory = f"{prompt}\n\nUser preferences (from WhatsApp replies):\n{prefs}\n\nPast sightings log:\n{sightings}"
        print(prompt_with_memory)
        agent(prompt_with_memory)
    else:
        sleep(0.5)
