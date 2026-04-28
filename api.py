"""
Argos Core - FastAPI wrapper
Exposes ArgosAgent as HTTP API without modifying agent.py
"""
import os
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from core.agent import ArgosAgent
from utils.logger_config import get_argos_logger

logger = get_argos_logger()
_agent: ArgosAgent | None = None


async def _warmup_chat_model() -> None:
    chat_model = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:1.7b")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            await c.post(
                f"{ollama_url}/api/generate",
                json={"model": chat_model, "prompt": "hi", "stream": False,
                      "options": {"num_predict": 1}, "keep_alive": -1},
            )
        logger.info(f"Chat model warmed up: {chat_model}")
    except Exception as e:
        logger.warning(f"Warmup failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    logger.info("Starting Argos API — initializing agent...")
    db_path = ArgosAgent.db_path()
    logger.info(f"Checkpoint DB: {db_path}")
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as memory:
        _agent = ArgosAgent(memory)
        logger.info("Agent ready.")
        await _warmup_chat_model()
        yield
    _agent = None


app = FastAPI(title="Argos Core API", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    model: str | None = None  # qué modelo respondió (para debug/UI)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    thread_id = request.thread_id or str(uuid.uuid4())
    try:
        response, model_used = await _agent.run(request.message, thread_id=thread_id)  # type: ignore[union-attr]
    except Exception as e:
        logger.error(f"Agent error on thread {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(response=response, thread_id=thread_id, model=model_used)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest"),
    }
