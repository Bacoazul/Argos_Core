"""
Argos Core - FastAPI wrapper
Exposes ArgosAgent as HTTP API without modifying agent.py
"""
import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from fastmcp.utilities.lifespan import combine_lifespans

from core.agent import ArgosAgent
from core.config import load_model_config
from core.mcp_server import mcp
from utils.logger_config import get_argos_logger

logger = get_argos_logger()
_agent: ArgosAgent | None = None


async def _warmup_knowledge() -> None:
    from core.knowledge import is_stale, rebuild, _embed_single
    loop = asyncio.get_event_loop()
    if is_stale():
        logger.info("Building knowledge index in background...")
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                count = await loop.run_in_executor(pool, rebuild)
            logger.info(f"Knowledge index ready: {count} chunks.")
        except Exception as e:
            logger.warning(f"Knowledge warmup failed (non-fatal): {e}")
            return
    else:
        logger.info("Knowledge index up to date.")
    # Pre-warm nomic-embed-text (primer llamado carga el modelo en GPU ~20s)
    try:
        await loop.run_in_executor(None, lambda: _embed_single("warmup"))
        logger.info("nomic-embed-text warmed up.")
    except Exception as e:
        logger.warning(f"Embed warmup failed (non-fatal): {e}")


async def _warmup_chat_model() -> None:
    cfg = load_model_config()
    chat_model = cfg.chat
    ollama_url = cfg.ollama_base_url
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
        # Pre-warm knowledge index en background — no bloquea el startup
        asyncio.create_task(_warmup_knowledge())
        yield
    _agent = None


# MCP server montado como sub-app ASGI (streamable-http).
# path="/" interno + mount en "/mcp" → endpoint público POST /mcp, sin tapar
# las rutas REST existentes (/chat, /health, /knowledge/query).
# combine_lifespans corre el lifespan de Argos (AsyncSqliteSaver) Y el del
# session manager de FastMCP — sin este último el MCP no inicializa.
mcp_app = mcp.http_app(path="/", transport="streamable-http")

app = FastAPI(
    title="Argos Core API",
    lifespan=combine_lifespans(lifespan, mcp_app.lifespan),
)
app.mount("/mcp", mcp_app)


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


@app.get("/knowledge/query")
async def knowledge_query(q: str, n: int = 6) -> dict:
    """Semantic search sobre proyectos de Chucho. Usado por el dispatcher."""
    from core.knowledge import query as kb_query
    loop = asyncio.get_event_loop()
    context = await loop.run_in_executor(None, lambda: kb_query(q, n))
    return {"context": context}


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": load_model_config().agent,
    }
