# agentic-wildlife-cam

Start ngrok with `ngrok http 8000`
Start uvicorn webhook server to pick up usr messages with `uvicorn webhook_server:app --port 8000` 
Copy the ngrok URL into the .env file as it will be different from last time, and set it in the Twilio Console under Sandox Settings > When a message comes in
Start agent with `python agent.py`
