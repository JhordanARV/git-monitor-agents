import os
from typing import List, Dict
from crewai import Agent, Task, Crew
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CrewAnalyzer:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("No se encontró OPENAI_API_KEY en las variables de entorno")
            raise ValueError("OPENAI_API_KEY no está configurada")
            
        logger.info("Inicializando CrewAnalyzer")
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",  # Usando gpt-3.5 que es más económico
            temperature=0,
            api_key=api_key
        )

    def format_changes_for_analysis(self, changes: List[Dict]) -> str:
        """Formatea los cambios para un mejor análisis"""
        formatted = []
        for change in changes:
            if change['type'] == 'commit':
                formatted.append(
                    f"Commit por {change['author']}:\n"
                    f"Mensaje: {change['message']}\n"
                    f"Archivos modificados: {', '.join(change['files'])}\n"
                    f"Estadísticas: {change['stats']}\n"
                )
            else:  # local_change
                formatted.append(
                    f"Cambio local en {change['path']}:\n"
                    f"Tipo: {change['event_type']}\n"
                    f"Estado: {change['description']}\n"  # Usar la descripción amigable
                    f"Fecha: {change['date']}\n"
                    f"Contenido modificado: {change['content'][:200] + '...' if len(change['content']) > 200 else change['content']}\n"
                )
        return "\n---\n".join(formatted)

    def analyze_changes(self, changes: List[Dict]) -> str:
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
                verbose=True
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
                verbose=True
            )

            logger.info("Iniciando análisis con CrewAI")
            result = crew.kickoff()
            logger.info("Análisis completado exitosamente")
            return result
        except Exception as e:
            logger.error(f"Error durante el análisis: {str(e)}")
            return self.fallback_analysis(changes)
    
    def fallback_analysis(self, changes: List[Dict]) -> str:
        """Análisis de respaldo cuando falla OpenAI"""
        try:
            summary_parts = []
            for change in changes:
                if change['type'] == 'commit':
                    summary = f"🔵 *Commit por {change['author']}*\n"
                    summary += f"📝 Mensaje: {change['message']}\n"
                    summary += f"📁 Archivos: {', '.join(change['files'])}\n"
                    if 'stats' in change:
                        stats = change['stats']
                        summary += f"📊 Cambios: +{stats['insertions']} -{stats['deletions']} en {stats['files']} archivos\n"
                else:  # local_change
                    summary = f"🟡 *Cambio Local*\n"
                    summary += f"📄 Archivo: {change['path']}\n"
                    summary += f"🔄 Tipo: {change['event_type']}\n"
                    summary += f"📌 Estado: {change['description']}\n"  # Usar la descripción amigable
                    summary += f"⏰ Fecha: {change['date']}\n"
                    
                    # Mostrar preview del contenido si existe
                    if change.get('content'):
                        preview = change['content'][:100] + '...' if len(change['content']) > 100 else change['content']
                        summary += f"💡 Preview:\n```\n{preview}\n```\n"
                
                summary_parts.append(summary)
            
            return "\n\n".join(summary_parts)
        except Exception as e:
            logger.error(f"Error en análisis de respaldo: {e}")
            return "⚠️ No se pudo generar el análisis de los cambios"
