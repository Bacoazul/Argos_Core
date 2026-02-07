"""
Argos Core - Main Entry Point
Phase 3: Orchestration with Persistent Session
"""
import sys
import uuid
from utils.logger_config import get_argos_logger
from core.agent import ArgosAgent

logger = get_argos_logger()

def main():
    logger.info("ARGOS CORE - ORCHESTRATION MODE ONLINE")
    
    try:
        # 1. Inicializar el Agente (Carga LangGraph + Ollama)
        bot = ArgosAgent()
        
        # Generar ID único para esta sesión
        session_id = str(uuid.uuid4())
        logger.info(f"Session ID generated: {session_id}")
        
        print(f"\n🤖 ARGOS ONLINE [Session: {session_id[:8]}]")
        print("(Type 'exit' to quit, 'new' to reset memory)\n")
        
        # 2. Bucle de Chat Infinito
        while True:
            try:
                user_input = input("USER > ")
            except EOFError:
                break
            
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if user_input.lower() == "new":
                session_id = str(uuid.uuid4())
                print(f"\n🧹 Memory Wiped. New Session: {session_id[:8]}\n")
                continue

            if not user_input.strip():
                continue

            # 3. El Agente Ejecuta su Ciclo con Memoria
            response = bot.run(user_input, thread_id=session_id)
            
            print(f"\nARGOS >\n{response}\n")
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n🛑 Desconexión forzada.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"System Crash: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()