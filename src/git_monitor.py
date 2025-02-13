import git
from datetime import datetime
from typing import List, Dict, Optional, Union
from .file_watcher import FileWatcher
import logging
import os

logger = logging.getLogger(__name__)

class GitMonitor:
    def __init__(self, repo_path: str, branch: str = 'main'):
        self.repo_path = repo_path
        self.branch = branch
        logger.info(f"Inicializando GitMonitor para {repo_path} en rama {branch}")
        self.repo = git.Repo(repo_path)
        self.last_commit_sha = self.get_current_commit_sha()
        logger.info(f"Último commit conocido: {self.last_commit_sha}")
        self.file_watcher = FileWatcher(repo_path, self.handle_file_change)
        self.file_changes = []

    def get_current_commit_sha(self) -> str:
        return self.repo.heads[self.branch].commit.hexsha

    def handle_file_change(self, change: Dict):
        """Maneja los cambios detectados en archivos locales"""
        try:
            file_path = change['path']
            abs_path = os.path.join(self.repo_path, file_path)
            
            # Ignorar archivos que no existen o están en .git
            if not os.path.exists(abs_path) or '.git' in file_path:
                logger.debug(f"Ignorando archivo: {file_path} (no existe o es .git)")
                return
                
            logger.info(f"Cambio local detectado en: {file_path}")
            
            # Obtener el estado de Git
            status = self.get_file_status(file_path)
            logger.debug(f"Estado Git para {file_path}: {status}")
            
            # Solo registrar cambios en archivos tracked por Git o nuevos archivos añadidos
            if status not in ['??', '']:  # Ignorar archivos no tracked y sin estado
                # Obtener el contenido del archivo si existe y no es binario
                content = ""
                try:
                    if os.path.exists(abs_path) and not self.is_binary_file(abs_path):
                        with open(abs_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                except Exception as e:
                    logger.warning(f"No se pudo leer el contenido de {file_path}: {e}")
                
                self.file_changes.append({
                    'type': 'local_change',
                    'path': file_path,
                    'event_type': change['event_type'],
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': status,
                    'content': content[:1000] if content else "",  # Limitar el contenido a 1000 caracteres
                    'description': self.get_status_description(status)  # Añadir descripción del estado
                })
                logger.info(f"Cambio registrado para {file_path} con estado {status}")
            else:
                logger.debug(f"Ignorando archivo no tracked: {file_path}")
                
        except Exception as e:
            logger.error(f"Error al manejar cambio de archivo: {e}")

    def is_binary_file(self, file_path: str) -> bool:
        """Detecta si un archivo es binario"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return True

    def get_status_description(self, status: str) -> str:
        """Retorna una descripción amigable del estado de Git"""
        status_map = {
            'M': 'Modificado',
            'A': 'Añadido',
            'D': 'Eliminado',
            'R': 'Renombrado',
            'C': 'Copiado',
            'U': 'Actualizado pero sin mezclar',
            'AM': 'Añadido y modificado',
            'MM': 'Modificado en staged y working directory',
            '??': 'No tracked'
        }
        return status_map.get(status, f'Estado desconocido: {status}')

    def get_file_status(self, file_path: str) -> str:
        """Obtiene el estado de Git para un archivo"""
        try:
            status = self.repo.git.status('--porcelain', file_path).split()[0]
            logger.debug(f"Estado de Git para {file_path}: {status}")
            return status
        except Exception as e:
            logger.debug(f"No se pudo obtener estado de Git para {file_path}: {e}")
            return '??'

    def start_monitoring(self):
        """Inicia el monitoreo de archivos"""
        logger.info("Iniciando monitoreo de archivos")
        self.file_watcher.start()

    def stop_monitoring(self):
        """Detiene el monitoreo de archivos"""
        logger.info("Deteniendo monitoreo de archivos")
        self.file_watcher.stop()

    def check_for_changes(self) -> Optional[Dict[str, List[Dict]]]:
        """
        Verifica cambios tanto en commits como en archivos locales
        Retorna un diccionario con ambos tipos de cambios si existen
        """
        changes = {}
        
        try:
            # Pull latest changes
            logger.info("Obteniendo cambios remotos...")
            self.repo.remotes.origin.pull()
            
            current_sha = self.get_current_commit_sha()
            
            # Check for new commits
            if current_sha != self.last_commit_sha:
                logger.info(f"Nuevos commits detectados. Último: {current_sha}")
                commits = list(self.repo.iter_commits(
                    f'{self.last_commit_sha}..{current_sha}'
                ))

                commit_changes = []
                for commit in commits:
                    logger.info(f"Procesando commit: {commit.hexsha[:8]} - {commit.message.splitlines()[0]}")
                    
                    # Obtener los cambios detallados del commit
                    diffs = []
                    for diff in commit.diff(commit.parents[0] if commit.parents else git.NULL_TREE):
                        if diff.a_path:
                            diffs.append({
                                'file': diff.a_path,
                                'type': diff.change_type,
                                'insertions': diff.diff.count(b'+'),
                                'deletions': diff.diff.count(b'-')
                            })
                    
                    commit_changes.append({
                        'type': 'commit',
                        'sha': commit.hexsha,
                        'author': commit.author.name,
                        'message': commit.message,
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'files': list(commit.stats.files.keys()),
                        'stats': commit.stats.total,
                        'diffs': diffs
                    })
                
                if commit_changes:
                    changes['commits'] = commit_changes
                    self.last_commit_sha = current_sha

            # Check for local changes
            if self.file_changes:
                logger.info(f"Procesando {len(self.file_changes)} cambios locales")
                # Hacer una copia y solo limpiar si se procesan correctamente
                current_changes = self.file_changes.copy()
                changes['local_changes'] = current_changes
                
                # Solo limpiar los cambios si se agregaron correctamente al diccionario
                if changes.get('local_changes'):
                    self.file_changes = []
                    logger.info("Cambios locales procesados y limpiados")
                else:
                    logger.warning("No se pudieron procesar los cambios locales correctamente")

            if changes:
                logger.info(f"Se encontraron cambios: {list(changes.keys())}")
            return changes if changes else None
            
        except Exception as e:
            logger.exception(f"Error al verificar cambios: {e}")
            return None
