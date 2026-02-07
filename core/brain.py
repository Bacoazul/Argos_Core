"""
Argos Core - Brain Module
Handles direct interaction with the local LLM (Ollama) backend.
"""
import ollama
from typing import List, Dict, Optional
from utils.logger_config import get_argos_logger

logger = get_argos_logger()

class ArgosBrain:
    """
    Primary interface for the Logic Brain (Qwen3).
    """

    def __init__(self, 
                 model_name: str = "qwen3-coder-next:latest", 
                 temperature: float = 0.7, 
                 context_window: int = 32768,
                 system_prompt: str = ""):
        """
        Initialize the Brain with a specific persona.
        """
        self.model = model_name
        self.system_prompt = system_prompt
        self.options = {
            "temperature": temperature,
            "num_ctx": context_window
        }
        logger.info(f"ArgosBrain initialized with model: {self.model}")

    def think(self, prompt: str) -> Optional[str]:
        """
        Single-shot reasoning generation with System Prompt injection.
        """
        logger.debug(f"Brain received think request: {prompt[:50]}...")
        
        try:
            # Inject System Prompt via the 'system' parameter in Ollama API
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                system=self.system_prompt,  # <--- INJECTION POINT
                options=self.options
            )
            
            output = response.get('response', '')
            logger.info("Brain successfully generated response.")
            return output
            
        except Exception as e:
            logger.exception("Fatal error during brain inference.")
            return None

    def chat(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Chat inference. Ensures System Prompt is the first message.
        """
        # Prepend system prompt if not present
        if self.system_prompt and (not messages or messages[0].get('role') != 'system'):
            messages.insert(0, {'role': 'system', 'content': self.system_prompt})

        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options=self.options
            )
            output = response.get('message', {}).get('content', '')
            return output
        except Exception:
            logger.exception("Fatal error during chat inference.")
            return None