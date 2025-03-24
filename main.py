import os
import time
import schedule
import logging
import sys
import argparse
from dotenv import load_dotenv
from src.git_monitor import GitMonitor
from src.slack_notifier import SlackNotifier
from src.module_manager import ModuleManager
from src.interfaces.web_ui import init_app, start_server
import threading
from datetime import datetime

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
        # Parsear argumentos de línea de comandos
        parser = argparse.ArgumentParser(description='Git Monitor con arquitectura modular')
        parser.add_argument('--config', type=str, default='config.yaml', help='Ruta al archivo de configuración')
        parser.add_argument('--web', action='store_true', help='Iniciar interfaz web de configuración')
        parser.add_argument('--web-port', type=int, default=5000, help='Puerto para la interfaz web')
        args = parser.parse_args()
        
        logger.info("Iniciando el monitor de Git...")
        
        # Inicializar el gestor de módulos
        logger.info(f"Cargando configuración desde {args.config}")
        module_manager = ModuleManager(args.config)
        
        # Iniciar interfaz web si se solicita
        if args.web:
            logger.info(f"Iniciando interfaz web en puerto {args.web_port}")
            app = init_app(args.config)
            web_thread = threading.Thread(
                target=start_server,
                kwargs={'host': '0.0.0.0', 'port': args.web_port, 'debug': False}
            )
            web_thread.daemon = True
            web_thread.start()
            logger.info(f"Interfaz web disponible en http://localhost:{args.web_port}")
        
        # Obtener configuración
        config = module_manager.config_manager.get_config()
        repo_path = config.get('core', {}).get('repo_path', os.getenv('REPO_PATH'))
        branch = config.get('core', {}).get('branch', os.getenv('REPO_BRANCH', 'main'))
        poll_interval = config.get('core', {}).get('poll_interval', 300)
        
        # Initialize components
        git_monitor = GitMonitor(
            repo_path=repo_path,
            branch=branch
        )
        
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
                    
                    # Procesar cambios con los módulos
                    if 'commits' in changes:
                        logger.info(f"Procesando {len(changes['commits'])} commits nuevos")
                        for commit in changes['commits']:
                            # Añadir información del repositorio
                            commit['repo_path'] = repo_path
                            
                            # Procesar con todos los módulos
                            results = module_manager.process_event(commit)
                            
                            # Enviar resultados a Slack
                            if results:
                                for result in results:
                                    if result and 'module' in result:
                                        module_name = result['module']
                                        logger.info(f"Enviando resultados de {module_name} a Slack")
                                        slack_notifier.send_message(f"📊 Resultados de {module_name} para commit {commit['sha'][:7]}:\n```\n{result.get('summary', 'Sin resumen')}\n```")
                    
                    if 'local_changes' in changes:
                        local_changes = changes['local_changes']
                        logger.info(f"Procesando {len(local_changes)} cambios locales")
                        
                        for change in local_changes:
                            # Añadir información del repositorio
                            change['repo_path'] = repo_path
                            
                            # Procesar con todos los módulos
                            results = module_manager.process_event(change)
                            
                            # Enviar resultados a Slack
                            if results:
                                for result in results:
                                    if result and 'module' in result:
                                        module_name = result['module']
                                        logger.info(f"Enviando resultados de {module_name} a Slack para cambios locales")
                                        slack_notifier.send_message(f"📝 Resultados de {module_name} para cambios locales:\n```\n{result.get('summary', 'Sin resumen')}\n```")
                    
                    # Procesar cambios en el área de staging
                    if 'staged' in changes and changes['staged']:
                        logger.info(f"Procesando {len(changes['staged'])} archivos en staging area")
                        
                        # Crear un evento para todos los archivos en staging
                        staged_event = {
                            'type': 'staged_files',
                            'files': changes['staged'],
                            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'repo_path': repo_path
                        }
                        
                        # Procesar con todos los módulos
                        results = module_manager.process_event(staged_event)
                        
                        # Enviar resultados a Slack
                        if results:
                            for result in results:
                                if result and 'module' in result:
                                    module_name = result['module']
                                    logger.info(f"Enviando resultados de {module_name} a Slack para cambios en staging")
                                    slack_notifier.send_message(f"📝 Resultados de {module_name} para cambios en staging:\n```\n{result.get('summary', 'Sin resumen')}\n```")
                else:
                    logger.debug("No se detectaron cambios")
            except Exception as e:
                logger.exception("Error durante la verificación de cambios")

        # Start file monitoring
        git_monitor.start_monitoring()
        logger.info("Monitoreo de archivos iniciado")

        try:
            # Schedule the job to run based on config
            schedule.every(poll_interval).seconds.do(check_and_notify)
            logger.info(f"Programador configurado para revisar cada {poll_interval} segundos")

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
