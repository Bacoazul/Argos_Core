"""
Argos Core - Agent Module (LangGraph Architecture)
Phase 5: Docker Ready + Robust State Handling
"""
import os
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from core.prompts import get_system_prompt
from core.tools import ARGOS_TOOLS  # <--- ESTO DEBE EXISTIR
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class ArgosAgent:
    def __init__(self):
        logger.info("Initializing Argos Agent (Docker-Ready)...")
        
        # --- DOCKER NETWORK CONFIGURATION ---

        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen3-coder-next:latest") # <-- FIX DINÁMICO
        
        logger.info(f"Connecting to Brain at: {ollama_url} using model: {ollama_model}")

        # Configurar LLM con Tools
        llm = ChatOllama(
            model=ollama_model, # <-- AHORA LEE LA VARIABLE
            base_url=ollama_url,
            temperature=0.1,
            num_ctx=32768,         
            keep_alive=-1          
        )
        
        # Bind tools
        self.llm_with_tools = llm.bind_tools(ARGOS_TOOLS)
        self.memory = MemorySaver()
        self.app = self._build_brain()

    def _call_model(self, state: AgentState):
        return {"messages": [self.llm_with_tools.invoke(state["messages"])]}

    def _build_brain(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(ARGOS_TOOLS))

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=self.memory)

    def run(self, user_input: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1. Obtener estado actual de forma segura (Fix de Grok)
        # Usamos el getter de LangGraph para ver si ya hay historia
        state_snapshot = self.app.get_state(config) # type: ignore
        existing_messages = state_snapshot.values.get("messages", [])
        
        messages_to_send = []

        # 2. Inyectar System Prompt SOLO si es el primer mensaje del hilo
        if not existing_messages:
            logger.info(f"Starting new thread: {thread_id}")
            sys_prompt = get_system_prompt()
            messages_to_send.append(SystemMessage(content=sys_prompt))
        
        messages_to_send.append(HumanMessage(content=user_input))
        
        # 3. Invocar (LangGraph sumará estos mensajes a la memoria existente)
        # type: ignore para silenciar Pylance en el dict input
        result = self.app.invoke({"messages": messages_to_send}, config) # type: ignore
        
        return result["messages"][-1].content