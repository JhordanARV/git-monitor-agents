import os
import time
import schedule
import logging
import sys
from dotenv import load_dotenv
from src.git_monitor import GitMonitor
from src.crew_analyzer import CrewAnalyzer
from src.slack_notifier import SlackNotifier

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('git_monitor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    try:
        logger.info("Iniciando el monitor de Git...")
        
        # Initialize components
        git_monitor = GitMonitor(
            repo_path=os.getenv('REPO_PATH'),
            branch=os.getenv('REPO_BRANCH', 'main')
        )
        
        logger.info("Inicializando CrewAnalyzer...")
        crew_analyzer = CrewAnalyzer()
        
        logger.info("Inicializando SlackNotifier...")
        slack_notifier = SlackNotifier(
            token=os.getenv('SLACK_BOT_TOKEN'),
            channel=os.getenv('SLACK_CHANNEL_ID')
        )

        # Prueba inicial de Slack
        logger.info("Realizando prueba de conexión con Slack...")
        test_result = slack_notifier.send_message("🔄 Monitor de Git iniciado - Prueba de conexión")
        if not test_result:
            logger.error("Error en la prueba de conexión con Slack. Verifica las credenciales.")
            return

        def check_and_notify():
            logger.info("Verificando cambios...")
            # Check for new changes
            try:
                changes = git_monitor.check_for_changes()
                if changes:
                    logger.info(f"Cambios detectados: {changes.keys()}")
                    logger.debug(f"Contenido de cambios: {changes}")
                    
                    # Analyze changes with CrewAI
                    if 'commits' in changes:
                        logger.info(f"Analizando {len(changes['commits'])} commits nuevos")
                        try:
                            commit_analysis = crew_analyzer.analyze_changes(changes['commits'])
                            if commit_analysis:
                                logger.info("Enviando análisis de commits a Slack")
                                slack_notifier.send_message("*Nuevos commits detectados:*\n" + commit_analysis)
                            else:
                                logger.error("El análisis de commits retornó None")
                        except Exception as e:
                            logger.exception("Error analizando commits")
                    
                    if 'local_changes' in changes:
                        local_changes = changes['local_changes']
                        logger.info(f"Analizando {len(local_changes)} cambios locales")
                        logger.debug(f"Cambios locales: {local_changes}")
                        
                        # Si hay error en el análisis, usar el fallback
                        try:
                            local_analysis = crew_analyzer.analyze_changes(local_changes)
                            if not local_analysis:
                                logger.warning("Análisis retornó None, usando fallback")
                                local_analysis = crew_analyzer.fallback_analysis(local_changes)
                        except Exception as e:
                            logger.exception("Error en análisis, usando fallback")
                            local_analysis = crew_analyzer.fallback_analysis(local_changes)
                            
                        if local_analysis:
                            logger.info("Enviando análisis de cambios locales a Slack")
                            message = "*Cambios locales detectados:*\n" + local_analysis
                            if not slack_notifier.send_message(message):
                                logger.error("Error enviando mensaje a Slack")
                        else:
                            logger.error("No se pudo obtener análisis ni fallback para cambios locales")
                else:
                    logger.debug("No se detectaron cambios")
            except Exception as e:
                logger.exception("Error durante la verificación de cambios")

        # Start file monitoring
        git_monitor.start_monitoring()
        logger.info("Monitoreo de archivos iniciado")

        try:
            # Schedule the job to run every 5 minutes
            schedule.every(5).minutes.do(check_and_notify)
            logger.info("Programador configurado para revisar cada 5 minutos")

            # Run first check immediately
            logger.info("Ejecutando primera verificación...")
            check_and_notify()

            # Run continuously
            logger.info("Iniciando bucle principal...")
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nDeteniendo el monitoreo...")
            git_monitor.stop_monitoring()
        except Exception as e:
            logger.exception("Error en el bucle principal")
            git_monitor.stop_monitoring()
    except Exception as e:
        logger.exception("Error fatal en la aplicación")

if __name__ == "__main__":
    main()
