"""
Argos Core - Main Entry Point
Phase 2: Persona Activation
"""
import sys
from utils.logger_config import get_argos_logger
from core.brain import ArgosBrain
from core.prompts import get_system_prompt

logger = get_argos_logger()

def main():
    logger.info("ARGOS CORE - SOVEREIGN BOOT SEQUENCE")

    try:
        # 1. Load Persona
        sys_prompt = get_system_prompt()
        logger.info("Loading Sovereign Persona (XML Architecture)...")
        
        # 2. Initialize Brain with Persona
        brain = ArgosBrain(
            model_name="qwen3-coder-next:latest", 
            system_prompt=sys_prompt
        )
        
        # 3. Test Identity
        test_prompt = "Who are you and what is your primary constraint?"
        logger.info(f"Identity Check: '{test_prompt}'")
        
        response = brain.think(test_prompt)
        
        if response:
            print(f"\n{response}\n") # Should now follow [Answer]/[Rationale] format
        else:
            logger.critical("❌ CORTEX SILENT")

    except KeyboardInterrupt:
        sys.exit(130)

if __name__ == "__main__":
    main()