import anthropic
import dotenv
from pathlib import Path
import subprocess
from gpiozero import LED, Buzzer
from time import sleep
from sense_hat import SenseHat

from picamzero import Camera
from datetime import datetime
cam = Camera()

dotenv.load_dotenv()

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "set_display_colour",
        "description": "Set the colour of the 8x8 pixel display using RGB",
        "input_schema": {
            "type": "object",
            "properties": {
                "red": {"type": "integer"},
                "green": {"type": "integer"},
                "blue": {"type": "integer"}
            },
            "required": ["red", "green", "blue"]
        }
    },
    {
        "name": "set_display_pixels",
        "description": "Set colours of the 8x8 display via a list of 64 lists of RGB values, one for each pixel",
        "input_schema": {
            "type": "object",
            "properties": {
                "pixels": {"type": "array"}
            },
            "required": ["pixels"]
        }
    },
    {
        "name": "start_video",
        "description": "Take a 10 second recording, returns content of video",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def set_display_colour(red: int, green: int, blue: int) -> str:
    sense = SenseHat()
    colour = [red, green, blue]
    pixels = [ colour ] * 64
    sense.set_pixels(pixels)
    return "Done!"

def set_display_pixels(pixels) -> str:
    sense = SenseHat()
    sense.set_pixels(pixels)
    return "Done!" 

def start_video() -> str:
    now = datetime.now()
    cam.take_video(f"temp/wildlife.mp4", 1)
    uploaded = client.beta.files.upload(
        file=(f"wildlife.mp4", open(f"temp/wildlife.mp4", "rb"), "application/mp4" )
    )
    print(uploaded)
    return str(uploaded)

def run_tool(name: str, arguments: dict) -> str:
    try:
        if name == "set_display_colour":
            return set_display_colour(int(arguments["red"]), int(arguments["green"]), int(arguments["blue"]))
        if name == "set_display_pixels":
            return set_display_pixels(arguments["pixels"])
        if name == "start_video":
            return start_video()

    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    raise ValueError(f"Unknown tool: {name}")

def agent(prompt: str, max_turns: int=10) -> str:
    messages = [{"role": "user", "content": prompt}]

    for turn in range(1, max_turns + 1):
        print(f"\n--- Turn {turn} ---")

        response = client.messages.create(
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
                is_error = result.startswith("Error:")
                print(f"[tool result] {result[:200]}{'...' if len(result) > 200 else ''}")
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

# agent("""
#     turn the display into a checkerboard of blue and red
# """)

agent("take a video and summarise what's in it")
