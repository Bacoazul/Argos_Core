"""
Argos Core - FastAPI wrapper
Exposes ArgosAgent as HTTP API without modifying agent.py
"""
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.agent import ArgosAgent
from utils.logger_config import get_argos_logger

logger = get_argos_logger()
_agent: ArgosAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    logger.info("Starting Argos API — initializing agent...")
    _agent = ArgosAgent()
    logger.info("Agent ready.")
    yield
    _agent = None


app = FastAPI(title="Argos Core API", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.thread_id or str(uuid.uuid4())
    try:
        response = _agent.run(request.message, thread_id=thread_id)  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Agent error on thread {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(response=response, thread_id=thread_id)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest"),
    }
