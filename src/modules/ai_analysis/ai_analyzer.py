import os
from typing import List, Dict, Optional
from crewai import Agent, Task, Crew
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from src.utils.claude_client import ClaudeClient
import logging
from datetime import datetime
from src.core.base_module import BaseModule

logger = logging.getLogger(__name__)

class AIAnalyzer(BaseModule):
    """
    Módulo para analizar cambios en el código utilizando inteligencia artificial.
    Utiliza CrewAI para crear agentes que analizan los cambios y proporcionan insights.
    """
    
    def __init__(self, config=None):
        """
        Inicializa el analizador de IA.
        
        Args:
            config (dict, opcional): Configuración del módulo.
        """
        super().__init__(config)
        # No establecer self.name directamente, ya que es una propiedad en la clase base
        # self.name = "ai_analyzer"
        
        if self.is_enabled():
            self._initialize_llm()
    
    @classmethod
    def get_config_schema(cls):
        """
        Devuelve el esquema de configuración para este módulo.
        
        Returns:
            dict: Esquema de configuración.
        """
        return {
            'enabled': {
                'type': 'boolean',
                'description': 'Habilitar o deshabilitar el módulo',
                'default': True
            },
            'openai_model': {
                'type': 'string',
                'description': 'Modelo de OpenAI a utilizar',
                'default': 'gpt-3.5-turbo',
                'options': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']
            },
            'temperature': {
                'type': 'number',
                'description': 'Temperatura para la generación de texto (0-1)',
                'default': 0,
                'min': 0,
                'max': 1
            },
            'verbose': {
                'type': 'boolean',
                'description': 'Mostrar información detallada durante el análisis',
                'default': True
            }
        }

    def _initialize_llm(self):
        """Inicializa el modelo de lenguaje según la configuración."""
        self.ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
        
        if self.ai_provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("No se encontró OPENAI_API_KEY en las variables de entorno")
                raise ValueError("OPENAI_API_KEY no está configurada")
                
            logger.info("Inicializando AIAnalyzer con OpenAI")
            self.llm = ChatOpenAI(
                model_name=self.config.get('openai_model', "gpt-3.5-turbo"),
                temperature=self.config.get('temperature', 0),
                api_key=api_key
            )
        elif self.ai_provider == 'claude':
            logger.info("Inicializando AIAnalyzer con Claude")
            claude_client = ClaudeClient()
            self.llm = claude_client.llm
        else:
            logger.error(f"Proveedor de AI no válido: {self.ai_provider}")
            raise ValueError(f"AI_PROVIDER debe ser 'openai' o 'claude', no '{self.ai_provider}'")

    def format_changes_for_analysis(self, changes: List[Dict]) -> str:
        """
        Formatea los cambios para un mejor análisis.
        
        Args:
            changes (List[Dict]): Lista de cambios a formatear.
            
        Returns:
            str: Texto formateado con los cambios.
        """
        formatted = []
        for change in changes:
            if change.get('type') == 'commit':
                formatted.append(
                    f"Commit por {change.get('author', 'Desconocido')}:\n"
                    f"Mensaje: {change.get('message', 'Sin mensaje')}\n"
                    f"Archivos modificados: {', '.join(change.get('files', []))}\n"
                    f"Estadísticas: {change.get('stats', {})}\n"
                )
            elif change.get('type') == 'staged_file':
                formatted.append(
                    f"Archivo en staging: {change.get('path', 'Desconocido')}\n"
                    f"Estado: {change.get('status', 'Desconocido')}\n"
                    f"Contenido: {change.get('content', '')[:200] + '...' if len(change.get('content', '')) > 200 else change.get('content', '')}\n"
                )
            else:  # local_change u otros tipos
                formatted.append(
                    f"Cambio en {change.get('path', 'Desconocido')}:\n"
                    f"Tipo: {change.get('event_type', change.get('type', 'Desconocido'))}\n"
                    f"Estado: {change.get('description', change.get('status', 'Desconocido'))}\n"
                    f"Fecha: {change.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n"
                    f"Contenido modificado: {change.get('content', '')[:200] + '...' if len(change.get('content', '')) > 200 else change.get('content', '')}\n"
                )
        return "\n---\n".join(formatted)

    def analyze_changes(self, changes: List[Dict]) -> str:
        """
        Analiza los cambios utilizando CrewAI.
        
        Args:
            changes (List[Dict]): Lista de cambios a analizar.
            
        Returns:
            str: Resultado del análisis.
        """
        try:
            logger.info(f"Analizando cambios con CrewAI: {len(changes)} cambios")
            
            # Formatear los cambios para análisis
            changes_text = self.format_changes_for_analysis(changes)
            
            # Create agents
            analyzer = Agent(
                role='Code Analyzer',
                goal='Analyze code changes and provide technical insights',
                backstory='Expert code reviewer with experience in multiple programming languages',
                llm=self.llm,
                verbose=self.config.get('verbose', True)
            )

            # Create tasks
            analysis_task = Task(
                description=f"""Analiza los siguientes cambios y proporciona un resumen claro y conciso:

                {changes_text}

                Tu resumen debe incluir:
                1. Qué archivos fueron modificados
                2. Tipo de cambios realizados
                3. Impacto potencial de los cambios
                
                Formato tu respuesta usando Markdown y emojis para mejor legibilidad.
                """,
                agent=analyzer,
                expected_output="Un resumen técnico y claro de los cambios, formateado con Markdown y emojis"
            )

            # Create and run the crew
            crew = Crew(
                agents=[analyzer],
                tasks=[analysis_task],
                verbose=self.config.get('verbose', True)
            )

            logger.info("Iniciando análisis con CrewAI")
            result = crew.kickoff()
            logger.info("Análisis completado exitosamente")
            return result
        except Exception as e:
            logger.error(f"Error durante el análisis: {str(e)}")
            return self.fallback_analysis(changes)
    
    def fallback_analysis(self, changes: List[Dict]) -> str:
        """
        Análisis de respaldo cuando falla el análisis principal.
        
        Args:
            changes (List[Dict]): Lista de cambios a analizar.
            
        Returns:
            str: Resultado del análisis de respaldo.
        """
        try:
            summary_parts = []
            for change in changes:
                if change.get('type') == 'commit':
                    summary = f"🔵 *Commit por {change.get('author', 'Desconocido')}*\n"
                    summary += f"📝 Mensaje: {change.get('message', 'Sin mensaje')}\n"
                    summary += f"📁 Archivos: {', '.join(change.get('files', []))}\n"
                    if 'stats' in change:
                        stats = change['stats']
                        summary += f"📊 Cambios: +{stats.get('insertions', 0)} -{stats.get('deletions', 0)} en {stats.get('files', 0)} archivos\n"
                elif change.get('type') == 'staged_file':
                    summary = f"🟠 *Archivo en Staging*\n"
                    summary += f"📄 Archivo: {change.get('path', 'Desconocido')}\n"
                    summary += f"📌 Estado: {change.get('status', 'Desconocido')}\n"
                    
                    # Mostrar preview del contenido si existe
                    if change.get('content'):
                        preview = change['content'][:100] + '...' if len(change['content']) > 100 else change['content']
                        summary += f"💡 Preview:\n```\n{preview}\n```\n"
                else:  # local_change u otros tipos
                    summary = f"🟡 *Cambio Local*\n"
                    summary += f"📄 Archivo: {change.get('path', 'Desconocido')}\n"
                    summary += f"🔄 Tipo: {change.get('event_type', change.get('type', 'Desconocido'))}\n"
                    summary += f"📌 Estado: {change.get('description', change.get('status', 'Desconocido'))}\n"
                    summary += f"⏰ Fecha: {change.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n"
                    
                    # Mostrar preview del contenido si existe
                    if change.get('content'):
                        preview = change['content'][:100] + '...' if len(change['content']) > 100 else change['content']
                        summary += f"💡 Preview:\n```\n{preview}\n```\n"
                
                summary_parts.append(summary)
            
            return "\n\n".join(summary_parts)
        except Exception as e:
            logger.error(f"Error en análisis de respaldo: {e}")
            return "⚠️ No se pudo generar el análisis de los cambios"

    def process(self, event_data):
        """
        Procesa un evento y genera un análisis de los cambios.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            dict: Resultado del procesamiento.
        """
        if not self.is_enabled():
            logger.debug("Módulo AIAnalyzer deshabilitado")
            return None
            
        try:
            logger.info(f"Procesando evento con AIAnalyzer: {event_data.get('type', 'desconocido')}")
            
            changes = []
            
            # Procesar diferentes tipos de eventos
            if event_data.get('type') == 'commit':
                changes.append(event_data)
            elif event_data.get('type') == 'local_changes':
                changes.extend(event_data.get('files', []))
            elif event_data.get('type') == 'staged_files':
                # Convertir los archivos en staging a un formato adecuado para el análisis
                for file in event_data.get('files', []):
                    file_data = {
                        'type': 'staged_file',
                        'path': file.get('path', ''),
                        'status': file.get('status', ''),
                        'content': file.get('content', '')
                    }
                    changes.append(file_data)
            
            if not changes:
                logger.warning("No hay cambios para analizar")
                return None
                
            # Analizar los cambios
            analysis = self.analyze_changes(changes)
            
            # Devolver el resultado
            return {
                'module': self.name,
                'summary': analysis,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error al procesar evento en AIAnalyzer: {str(e)}")
            return {
                'module': self.name,
                'summary': f"⚠️ Error al analizar los cambios: {str(e)}",
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
