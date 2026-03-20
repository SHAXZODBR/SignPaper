import os
import sys
import asyncio

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request, Response
from telegram import Update
from bot.main import init_application

app = FastAPI()

# Global application instance
_application = None

async def get_application():
    global _application
    if _application is None:
        _application = await init_application()
        await _application.initialize()
    return _application

@app.get("/")
async def root():
    return {"status": "ok", "message": "SignPaper Bot API is running"}

@app.post("/api/webhook")
async def webhook_handler(request: Request):
    """Handle incoming Telegram updates."""
    application = await get_application()
    
    # Parse update from request body
    data = await request.json()
    update = Update.de_json(data, application.bot)
    
    # Process update
    # In a serverless environment, we don't use run_polling.
    # We process the update directly.
    await application.process_update(update)
    
    return Response(status_code=200)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
