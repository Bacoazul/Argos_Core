"""
Argos Core - Agent Module (LangGraph Architecture)
Updated: Feb 2026 (MemorySaver + Pylance Fixes)
"""
import uuid
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from core.prompts import get_system_prompt
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class ArgosAgent:
    """
    Reactive Agent with Short-term Memory (Checkpointer).
    """
    def __init__(self):
        logger.info("Initializing Argos Memory-Aware Agent...")
        
        # Configuración SOTA para Coding/Logic en RTX 5090
        self.llm = ChatOllama(
            model="qwen3-coder-next:latest",
            temperature=0.2,       
            num_ctx=32768,         
            keep_alive=-1          
        )
        
        self.memory = MemorySaver()
        self.app = self._build_brain()

    def _call_model(self, state: AgentState):
        messages = state["messages"]
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    def _build_brain(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._call_model)
        workflow.set_entry_point("agent")
        workflow.add_edge("agent", END)
        
        return workflow.compile(checkpointer=self.memory)

    def run(self, user_input: str, thread_id: str):
        """
        Ejecuta el ciclo pensando en el contexto del hilo actual.
        """
        # Configuración del hilo de memoria
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1. Verificar estado actual (Silenciamos el error de tipo estricto)
        current_state = self.app.get_state(config) # type: ignore
        
        messages_to_send = []

        # 2. Si es una sesión nueva, inyectamos la personalidad
        if not current_state.values:
            logger.info(f"Starting new thread: {thread_id}")
            sys_prompt = get_system_prompt()
            messages_to_send.append(SystemMessage(content=sys_prompt))
        
        # 3. Añadir mensaje del usuario
        messages_to_send.append(HumanMessage(content=user_input))
        
        inputs = {"messages": messages_to_send}
        
        # 4. Ejecutar Grafo (Silenciamos el error de tipo estricto)
        result = self.app.invoke(inputs, config) # type: ignore
        
        return result["messages"][-1].content