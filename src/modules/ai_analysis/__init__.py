"""
Módulo para análisis de código utilizando inteligencia artificial.
"""

from src.core.module_registry import ModuleRegistry
from src.modules.ai_analysis.ai_analyzer import AIAnalyzer

# Registrar el módulo usando el decorador
ModuleRegistry.register(AIAnalyzer)
