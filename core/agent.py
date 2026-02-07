"""
Argos Core - Agent Module (LangGraph Architecture)
Phase 4: Tool Integration (ReAct Pattern)
"""
import json
from typing import Annotated, TypedDict, List, Union
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition # <--- IMPORTANTE: Nodos preconstruidos
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, AIMessage

from core.prompts import get_system_prompt
from core.tools import ARGOS_TOOLS # <--- Importamos tus nuevas manos
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class ArgosAgent:
    def __init__(self):
        logger.info("Initializing Argos Agent with TOOLS...")
        
        # 1. Configurar LLM
        llm = ChatOllama(
            model="qwen3-coder-next:latest",
            temperature=0.1,       # Muy bajo para precisión usando herramientas
            num_ctx=32768,         
            keep_alive=-1          
        )
        
        # 2. BINDING: Enseñarle las herramientas al modelo
        # Esto permite que Qwen sepa qué funciones existen y cómo llamarlas (JSON)
        self.llm_with_tools = llm.bind_tools(ARGOS_TOOLS)
        
        self.memory = MemorySaver()
        self.app = self._build_brain()

    def _call_model(self, state: AgentState):
        """Nodo de Pensamiento"""
        messages = state["messages"]
        # Invocamos al modelo CON herramientas vinculadas
        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def _build_brain(self):
        workflow = StateGraph(AgentState)

        # Nodos
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(ARGOS_TOOLS)) # <--- Nodo que ejecuta las funciones reales

        # Bordes (Edges)
        workflow.add_edge(START, "agent")
        
        # Lógica Condicional: 
        # ¿El modelo decidió llamar a una herramienta? -> Ve a "tools"
        # ¿El modelo respondió texto final? -> Ve a END
        workflow.add_conditional_edges(
            "agent",
            tools_condition
        )
        
        # Si ejecutamos una herramienta, volvemos al agente para que interprete el resultado
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=self.memory)

    def run(self, user_input: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        
        # type: ignore para silenciar a Pylance
        current_state = self.app.get_state(config) # type: ignore
        messages_to_send = []

        if not current_state.values:
            logger.info(f"Starting new thread: {thread_id}")
            # Añadimos instrucción sobre herramientas al System Prompt
            sys_prompt = get_system_prompt()
            messages_to_send.append(SystemMessage(content=sys_prompt))
        
        messages_to_send.append(HumanMessage(content=user_input))
        
        inputs = {"messages": messages_to_send}
        
        # Ejecutar Grafo (puede hacer bucles: Pensar -> Herramienta -> Pensar -> Responder)
        result = self.app.invoke(inputs, config) # type: ignore
        
        # Retornamos el último mensaje (que debería ser la respuesta final)
        return result["messages"][-1].content