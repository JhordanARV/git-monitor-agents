from langchain_anthropic import ChatAnthropic
import os
import logging

logger = logging.getLogger(__name__)

class ClaudeClient:
    def __init__(self):
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            logger.error("No se encontró CLAUDE_API_KEY en las variables de entorno")
            raise ValueError("CLAUDE_API_KEY no está configurada")
            
        logger.info("Inicializando ClaudeClient")
        self.llm = ChatAnthropic(
            model_name="claude-3-sonnet-20240229",
            temperature=0,
            anthropic_api_key=api_key
        )
