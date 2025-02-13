from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable
import os
import time
import logging

logger = logging.getLogger(__name__)

class GitFileHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable, repo_path: str):
        self.callback = callback
        self.repo_path = repo_path
        self.last_modified = {}

    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Ignorar archivos .git
        if '.git' in event.src_path:
            return
            
        # Obtener la ruta relativa al repositorio
        rel_path = os.path.relpath(event.src_path, self.repo_path)
        
        # Evitar múltiples eventos para el mismo archivo
        current_time = time.time()
        if rel_path in self.last_modified:
            if current_time - self.last_modified[rel_path] < 1:  # Debounce de 1 segundo
                return
                
        self.last_modified[rel_path] = current_time
        
        logger.info(f"Archivo modificado: {rel_path}")
        self.callback({
            'type': 'file_change',
            'path': rel_path,
            'event_type': event.event_type
        })

class FileWatcher:
    def __init__(self, repo_path: str, callback: Callable):
        self.repo_path = repo_path
        self.callback = callback
        self.observer = None

    def start(self):
        """Inicia el observador de archivos"""
        logger.info(f"Iniciando observador de archivos en: {self.repo_path}")
        event_handler = GitFileHandler(self.callback, self.repo_path)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.repo_path, recursive=True)
        self.observer.start()
        logger.info("Observador de archivos iniciado correctamente")

    def stop(self):
        """Detiene el observador de archivos"""
        if self.observer:
            logger.info("Deteniendo observador de archivos...")
            self.observer.stop()
            self.observer.join()
            logger.info("Observador de archivos detenido")
