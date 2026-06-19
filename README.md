# agentic-wildlife-cam

Start ngrok with `ngrok http 8000`
Start agent with `python agent.py`
Start uvicorn webhook server to pick up usr messages with `uvicorn webhook_server:app --port 8000` 