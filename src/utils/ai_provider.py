"""
Utilidad para manejar los proveedores de IA (OpenAI, Claude, etc.)
"""

import os
import logging
from langchain_openai import ChatOpenAI
from src.utils.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

class AIProvider:
    """
    Clase para manejar los proveedores de IA y proporcionar instancias de LLM.
    """
    
    @staticmethod
    def get_llm(config=None):
        """
        Obtiene una instancia de LLM según la configuración y variables de entorno.
        
        Args:
            config (dict, opcional): Configuración específica para el LLM.
                Puede incluir 'openai_model', 'temperature', etc.
        
        Returns:
            object: Instancia de LLM (OpenAI o Claude).
        
        Raises:
            ValueError: Si no se encuentra la clave de API necesaria.
        """
        config = config or {}
        ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
        
        if ai_provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("No se encontró OPENAI_API_KEY en las variables de entorno")
                raise ValueError("OPENAI_API_KEY no está configurada")
                
            logger.info("Inicializando LLM con OpenAI")
            return ChatOpenAI(
                model_name=config.get('openai_model', "gpt-3.5-turbo"),
                temperature=config.get('temperature', 0),
                api_key=api_key
            )
        elif ai_provider == 'claude':
            logger.info("Inicializando LLM con Claude")
            claude_client = ClaudeClient()
            return claude_client.llm
        else:
            logger.warning(f"Proveedor de IA no reconocido: {ai_provider}, usando OpenAI por defecto")
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("No se encontró OPENAI_API_KEY en las variables de entorno")
                raise ValueError("OPENAI_API_KEY no está configurada")
                
            return ChatOpenAI(
                model_name=config.get('openai_model', "gpt-3.5-turbo"),
                temperature=config.get('temperature', 0),
                api_key=api_key
            )
