"""
Argos Core - Agent Module (LangGraph Architecture)

Arquitectura de dos caminos:
  CHAT  → qwen3:1.7b sin tools  → respuesta en ~1s
  AGENT → qwen3-coder con tools → respuesta en ~5-8s

El router es heurístico (keywords) — 0ms de overhead.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from core.prompts import get_system_prompt, get_chat_prompt
from core.tools import ARGOS_TOOLS
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

# Palabras clave que indican que el usuario quiere una tarea técnica con tools.
# Todo lo demás va al path de chat rápido.
_AGENT_KEYWORDS = (
    # Archivos y sistema
    "archivo", "file", "directorio", "folder", "carpeta",
    "lee ", "leer", "read", "write", "escribe", "guardar", "save",
    "lista los", "list ", "listame",
    # GitHub
    "github", "repo", "repositorio", "issue", "pull request", "commit",
    # Web
    "busca en internet", "busca en la web", "web search", "busca online",
    "investiga en internet", "googlea",
    # Código / técnico
    "código", "codigo", "script", "programa", "función", "funcion",
    "class ", "clase ", "import ", "instala", "dependencia",
    "docker", "contenedor", "container",
    "error en", "bug en", "debug",
    "refactor", "implementa", "crea el archivo", "crea un script",
    # Matemáticas (1.7B falla en aritmética, mejor el modelo pesado)
    "cuanto es ", "calcula ", "cuánto es ", "resultado de ",
    "multiplica", "divide", "suma ", "resta ",
)


import re as _re

_TIMESTAMP_RE = _re.compile(r"^\s*\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]\s*")


def _clean_chat_response(text: str) -> str:
    """Elimina timestamps que el modelo 1.7B a veces repite al inicio."""
    return _TIMESTAMP_RE.sub("", text).strip()


def _is_agent_query(text: str) -> bool:
    """True si el mensaje requiere tools o razonamiento técnico pesado."""
    t = text.lower()
    return any(kw in t for kw in _AGENT_KEYWORDS)


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


class ArgosAgent:
    """
    Agente con router heurístico CHAT / AGENT.
    Instanciar via ArgosAgent(memory) desde un contexto async con AsyncSqliteSaver.
    """

    def __init__(self, memory: AsyncSqliteSaver) -> None:
        logger.info("Initializing Argos Agent (dual-path router)...")

        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        agent_model = os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest")
        chat_model = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:1.7b")

        logger.info(f"Agent model: {agent_model} | Chat model: {chat_model}")

        # ── Chat path: ligero, sin tools, thinking desactivado ──────────────
        self.llm_chat = ChatOllama(
            model=chat_model,
            base_url=ollama_url,
            temperature=0.3,
            num_ctx=4096,
            keep_alive=-1,
        )

        # ── Agent path: pesado, con tools ───────────────────────────────────
        llm_agent = ChatOllama(
            model=agent_model,
            base_url=ollama_url,
            temperature=0.1,
            num_ctx=8192,
            keep_alive=-1,
        )
        self.llm_with_tools = llm_agent.bind_tools(ARGOS_TOOLS)
        self.app = self._build_brain(memory)
        logger.info("Agent brain compiled.")

    @staticmethod
    def db_path() -> Path:
        p = Path(os.getenv("CHECKPOINT_DB", "/data/argos/checkpoints.db"))
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # ── LangGraph nodes (agent path) ────────────────────────────────────────

    async def _call_model(self, state: AgentState) -> dict:
        return {"messages": [await self.llm_with_tools.ainvoke(state["messages"])]}

    def _build_brain(self, memory: AsyncSqliteSaver):
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(ARGOS_TOOLS))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=memory)

    # ── Entry point ─────────────────────────────────────────────────────────

    async def run(self, user_input: str, thread_id: str) -> tuple[str, str]:
        """Retorna (response, model_used)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        stamped_input = f"[{now}] {user_input}"

        if _is_agent_query(user_input):
            logger.info(f"[AGENT path] thread={thread_id}")
            response = await self._run_agent(stamped_input, thread_id)
            return response, os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest")
        else:
            logger.info(f"[CHAT path] thread={thread_id}")
            response = await self._run_chat(stamped_input)
            return response, os.getenv("OLLAMA_CHAT_MODEL", "qwen3:1.7b")

    async def _run_chat(self, stamped_input: str) -> str:
        """Path rápido: qwen3:1.7b sin tools, sin LangGraph overhead."""
        messages: list[BaseMessage] = [
            SystemMessage(content=get_chat_prompt()),
            HumanMessage(content=stamped_input),
        ]
        result = await self.llm_chat.ainvoke(messages)
        return _clean_chat_response(result.content)

    async def _run_agent(self, stamped_input: str, thread_id: str) -> str:
        """Path completo: qwen3-coder con tools y memoria persistente."""
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = await self.app.aget_state(config)
        existing_messages = state_snapshot.values.get("messages", [])

        messages_to_send: list[BaseMessage] = []
        if not existing_messages:
            logger.info(f"Starting new agent thread: {thread_id}")
            messages_to_send.append(SystemMessage(content=get_system_prompt()))

        messages_to_send.append(HumanMessage(content=stamped_input))

        result = await self.app.ainvoke(
            {"messages": messages_to_send},
            {**config, "recursion_limit": 10},
        )  # type: ignore
        return result["messages"][-1].content
