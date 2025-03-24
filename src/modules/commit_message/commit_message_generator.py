"""
Módulo para generar mensajes de commit automáticamente basados en los cambios.
"""

import os
import re
import logging
import git
import difflib
from collections import defaultdict
from src.core.base_module import BaseModule
from src.core.module_registry import ModuleRegistry
import json

logger = logging.getLogger(__name__)

@ModuleRegistry.register
class CommitMessageGenerator(BaseModule):
    """
    Genera mensajes de commit automáticamente basados en los cambios detectados.
    
    Este módulo analiza los cambios en el código y genera un mensaje de commit
    estructurado según las convenciones configuradas.
    """
    
    def __init__(self, config=None):
        """
        Inicializa el generador de mensajes de commit.
        
        Args:
            config (dict, opcional): Configuración del módulo.
        """
        super().__init__(config)
        self.convention = self.config.get('convention', 'conventional')
        self.language = self.config.get('language', 'spanish')
        self.include_scope = self.config.get('include_scope', True)
        self.include_body = self.config.get('include_body', True)
        self.include_footer = self.config.get('include_footer', False)
        self.max_length = int(self.config.get('max_length', 72))
        self.summarize_changes = self.config.get('summarize_changes', False)
        self.analyze_content = self.config.get('analyze_content', False)
        
        logger.info(f"CommitMessageGenerator inicializado con convención: {self.convention}")
        
    @classmethod
    def get_config_schema(cls):
        """
        Devuelve el esquema de configuración para este módulo.
        
        Returns:
            dict: Esquema de configuración.
        """
        return {
            'convention': {
                'type': 'string',
                'description': 'Convención a utilizar para los mensajes de commit',
                'enum': ['conventional', 'gitmoji', 'simple', 'custom'],
                'default': 'conventional'
            },
            'language': {
                'type': 'string',
                'description': 'Idioma para los mensajes de commit',
                'enum': ['spanish', 'english'],
                'default': 'spanish'
            },
            'include_scope': {
                'type': 'boolean',
                'description': 'Incluir el alcance en el mensaje (ej: feat(scope): message)',
                'default': True
            },
            'include_body': {
                'type': 'boolean',
                'description': 'Incluir cuerpo detallado en el mensaje',
                'default': True
            },
            'include_footer': {
                'type': 'boolean',
                'description': 'Incluir pie de página (referencias a issues, etc)',
                'default': False
            },
            'summarize_changes': {
                'type': 'boolean',
                'description': 'Generar un resumen de los cambios en lugar de listar todos los archivos',
                'default': False
            },
            'max_length': {
                'type': 'integer',
                'description': 'Longitud máxima del título del commit',
                'default': 72,
                'minimum': 20,
                'maximum': 100
            },
            'custom_template': {
                'type': 'string',
                'description': 'Plantilla personalizada para mensajes (solo para convención custom)',
                'default': '{type}: {message}'
            },
            'enabled': {
                'type': 'boolean',
                'description': 'Habilitar/deshabilitar este módulo',
                'default': True
            },
            'analyze_content': {
                'type': 'boolean',
                'description': 'Analizar el contenido de los archivos para generar el mensaje de commit',
                'default': False
            }
        }
    
    def process(self, event_data):
        """
        Procesa un evento y genera un mensaje de commit.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            dict: Resultado del procesamiento.
        """
        if not self.is_enabled():
            logger.debug("CommitMessageGenerator está deshabilitado")
            return None
            
        try:
            # Verificar si es un evento de cambio local
            if event_data.get('event_type') in ['modified', 'created', 'deleted']:
                return self._process_local_change(event_data)
            
            # Verificar si es un commit
            elif 'id' in event_data and 'message' in event_data:
                # No procesamos commits existentes, solo cambios locales
                return None
                
            else:
                logger.warning(f"Tipo de evento no soportado: {event_data}")
                return None
                
        except Exception as e:
            logger.exception(f"Error al generar mensaje de commit: {e}")
            return {
                'module': 'CommitMessageGenerator',
                'success': False,
                'summary': f"Error al generar mensaje de commit: {str(e)}"
            }
    
    def _process_local_change(self, change_data):
        """
        Procesa un cambio local y genera un mensaje de commit.
        
        Args:
            change_data (dict): Datos del cambio local.
            
        Returns:
            dict: Resultado del procesamiento.
        """
        path = change_data.get('path', '')
        event_type = change_data.get('event_type', '')
        content = change_data.get('content', '')
        
        # Determinar el tipo de cambio para el mensaje
        change_type = self._determine_change_type(event_type, path)
        
        # Determinar el alcance (scope) basado en la ruta del archivo
        scope = self._determine_scope(path) if self.include_scope else None
        
        # Generar el título del mensaje
        title = self._generate_title(change_type, scope, path, event_type)
        
        # Generar el cuerpo del mensaje si está habilitado
        body = self._generate_body(path, event_type, content) if self.include_body else None
        
        # Generar el pie de página si está habilitado
        footer = self._generate_footer(path, event_type) if self.include_footer else None
        
        # Construir el mensaje completo
        commit_message = self._build_commit_message(title, body, footer)
        
        return {
            'module': 'CommitMessageGenerator',
            'success': True,
            'summary': f"Mensaje de commit generado para {path}",
            'commit_message': commit_message
        }
    
    def _determine_change_type(self, event_type, path):
        """
        Determina el tipo de cambio para el mensaje de commit.
        
        Args:
            event_type (str): Tipo de evento (modified, created, deleted).
            path (str): Ruta del archivo.
            
        Returns:
            str: Tipo de cambio para el mensaje.
        """
        # Mapeo de tipos según la convención
        conventions = {
            'conventional': {
                'created': 'feat',
                'modified': 'fix' if '/fix/' in path.lower() or 'bug' in path.lower() else 'chore',
                'deleted': 'refactor'
            },
            'gitmoji': {
                'created': '✨',
                'modified': '🐛' if '/fix/' in path.lower() or 'bug' in path.lower() else '♻️',
                'deleted': '🔥'
            },
            'simple': {
                'created': 'Añadir' if self.language == 'spanish' else 'Add',
                'modified': 'Modificar' if self.language == 'spanish' else 'Update',
                'deleted': 'Eliminar' if self.language == 'spanish' else 'Remove'
            }
        }
        
        # Si es un archivo de documentación
        if path.endswith(('.md', '.rst', '.txt', 'README', 'CHANGELOG')):
            if self.convention == 'conventional':
                return 'docs'
            elif self.convention == 'gitmoji':
                return '📝'
        
        # Si es un archivo de prueba
        if '/test/' in path or path.startswith('test_') or path.endswith('_test.py'):
            if self.convention == 'conventional':
                return 'test'
            elif self.convention == 'gitmoji':
                return '✅'
        
        # Usar el mapeo predeterminado
        if self.convention in conventions:
            return conventions[self.convention].get(event_type, 'chore')
        
        # Convención personalizada o fallback
        return event_type
    
    def _determine_scope(self, path):
        """
        Determina el alcance (scope) basado en la ruta del archivo.
        
        Args:
            path (str): Ruta del archivo.
            
        Returns:
            str: Alcance para el mensaje de commit.
        """
        # Extraer componente principal de la ruta
        parts = path.split(os.path.sep)
        
        # Si está en src/modules, usar el nombre del módulo
        if len(parts) > 2 and parts[0] == 'src' and parts[1] == 'modules':
            return parts[2]
        
        # Si está en src/core, usar 'core'
        if len(parts) > 2 and parts[0] == 'src' and parts[1] == 'core':
            return 'core'
        
        # Si está en src/interfaces, usar 'ui'
        if len(parts) > 2 and parts[0] == 'src' and parts[1] == 'interfaces':
            return 'ui'
        
        # Si es un archivo en la raíz, usar el nombre sin extensión
        if len(parts) == 1:
            return os.path.splitext(parts[0])[0]
        
        # Usar el primer directorio no vacío
        for part in parts:
            if part and part != '.' and part != '..':
                return part
        
        return 'general'
    
    def _generate_title(self, change_type, scope, path, event_type):
        """
        Genera el título del mensaje de commit.
        
        Args:
            change_type (str): Tipo de cambio.
            scope (str): Alcance del cambio.
            path (str): Ruta del archivo.
            event_type (str): Tipo de evento.
            
        Returns:
            str: Título del mensaje de commit.
        """
        filename = os.path.basename(path)
        
        # Determinar mensaje según el idioma
        action_msg = {
            'created': 'añadir' if self.language == 'spanish' else 'add',
            'modified': 'actualizar' if self.language == 'spanish' else 'update',
            'deleted': 'eliminar' if self.language == 'spanish' else 'remove'
        }.get(event_type, event_type)
        
        # Construir mensaje según la convención
        if self.convention == 'conventional':
            if scope and self.include_scope:
                title = f"{change_type}({scope}): {action_msg} {filename}"
            else:
                title = f"{change_type}: {action_msg} {filename}"
                
        elif self.convention == 'gitmoji':
            title = f"{change_type} {action_msg} {filename}"
            
        elif self.convention == 'simple':
            title = f"{change_type} {filename}"
            
        elif self.convention == 'custom':
            template = self.config.get('custom_template', '{type}: {message}')
            title = template.format(
                type=change_type,
                scope=scope or '',
                message=f"{action_msg} {filename}",
                file=filename,
                action=action_msg
            )
        else:
            title = f"{change_type}: {filename}"
        
        # Limitar longitud
        if len(title) > self.max_length:
            title = title[:self.max_length-3] + "..."
            
        return title
    
    def _generate_body(self, path, event_type, content):
        """
        Genera el cuerpo del mensaje de commit.
        
        Args:
            path (str): Ruta del archivo.
            event_type (str): Tipo de evento.
            content (str): Contenido del cambio.
            
        Returns:
            str: Cuerpo del mensaje de commit.
        """
        # Mensajes según el idioma
        if self.language == 'spanish':
            if event_type == 'created':
                return f"Se ha creado el archivo {path}."
            elif event_type == 'modified':
                return f"Se ha modificado el archivo {path}."
            elif event_type == 'deleted':
                return f"Se ha eliminado el archivo {path}."
        else:  # english
            if event_type == 'created':
                return f"Created file {path}."
            elif event_type == 'modified':
                return f"Modified file {path}."
            elif event_type == 'deleted':
                return f"Deleted file {path}."
                
        return f"Changes in {path}"
    
    def _generate_footer(self, path, event_type):
        """
        Genera el pie de página del mensaje de commit.
        
        Args:
            path (str): Ruta del archivo.
            event_type (str): Tipo de evento.
            
        Returns:
            str: Pie de página del mensaje de commit.
        """
        # Por ahora, un pie de página simple
        if self.language == 'spanish':
            return "Generado automáticamente por CommitMessageGenerator"
        else:
            return "Automatically generated by CommitMessageGenerator"
    
    def _build_commit_message(self, title, body, footer):
        """
        Construye el mensaje de commit completo.
        
        Args:
            title (str): Título del mensaje.
            body (str): Cuerpo del mensaje.
            footer (str): Pie de página del mensaje.
            
        Returns:
            str: Mensaje de commit completo.
        """
        message = title
        
        if body:
            message += f"\n\n{body}"
            
        if footer:
            message += f"\n\n{footer}"
            
        return message
    
    def process_staged_changes(self, repo_path):
        """
        Procesa los cambios que están en stage (área de preparación) y genera un mensaje de commit.
        
        Args:
            repo_path (str): Ruta del repositorio Git.
            
        Returns:
            dict: Resultado del procesamiento con el mensaje de commit generado.
        """
        if not self.is_enabled():
            logger.debug("CommitMessageGenerator está deshabilitado")
            return None
            
        try:
            # Inicializar el repositorio Git
            repo = git.Repo(repo_path)
            
            # Obtener los cambios en stage
            staged_files = []
            for diff_item in repo.index.diff("HEAD"):
                staged_files.append({
                    'path': diff_item.a_path,
                    'event_type': self._get_event_type_from_diff(diff_item)
                })
                
            # Añadir archivos nuevos que no están siendo rastreados pero están en stage
            for untracked in repo.index.diff(None):
                staged_files.append({
                    'path': untracked.a_path,
                    'event_type': 'created'
                })
                
            if not staged_files:
                return {
                    'module': 'CommitMessageGenerator',
                    'success': False,
                    'summary': "No hay cambios en stage para generar un mensaje de commit"
                }
                
            # Generar mensaje basado en todos los cambios en stage
            return self._process_staged_files(staged_files)
                
        except Exception as e:
            logger.exception(f"Error al generar mensaje para cambios en stage: {e}")
            return {
                'module': 'CommitMessageGenerator',
                'success': False,
                'summary': f"Error al generar mensaje de commit: {str(e)}"
            }
    
    def _get_event_type_from_diff(self, diff_item):
        """
        Determina el tipo de evento a partir de un objeto diff de GitPython.
        
        Args:
            diff_item: Objeto diff de GitPython.
            
        Returns:
            str: Tipo de evento ('created', 'modified', 'deleted').
        """
        if diff_item.deleted_file:
            return 'deleted'
        elif diff_item.new_file:
            return 'created'
        else:
            return 'modified'
    
    def _process_staged_files(self, staged_files):
        """
        Procesa una lista de archivos en stage y genera un mensaje de commit.
        
        Args:
            staged_files (list): Lista de diccionarios con información de archivos en stage.
            
        Returns:
            dict: Resultado del procesamiento.
        """
        # Contar tipos de cambios
        change_counts = {'created': 0, 'modified': 0, 'deleted': 0}
        for file in staged_files:
            change_counts[file['event_type']] += 1
            
        # Determinar el tipo principal de cambio
        primary_change_type = max(change_counts.items(), key=lambda x: x[1])[0]
        
        # Determinar el alcance (scope) basado en las rutas de los archivos
        common_scope = self._determine_common_scope([file['path'] for file in staged_files]) if self.include_scope else None
        
        # Generar el título del mensaje
        change_type = self._determine_change_type(primary_change_type, staged_files[0]['path'])
        
        # Texto según el idioma configurado
        multiple_files_text = "múltiples archivos" if self.language == 'spanish' else "multiple files"
        title = self._generate_title(change_type, common_scope, 
                                    f"{multiple_files_text} ({len(staged_files)})", 
                                    primary_change_type)
        
        # Generar el cuerpo del mensaje si está habilitado
        body = None
        if self.include_body:
            # Texto según el idioma configurado
            changes_included_text = "Cambios incluidos:" if self.language == 'spanish' else "Changes included:"
            body_lines = [changes_included_text]
            
            # Obtener la ruta del repositorio desde la configuración
            repo_path = self.config.get('repo_path', '.')
            
            if self.summarize_changes:
                # Generar un resumen de los cambios
                if self.language == 'spanish':
                    summary_lines = [
                        f"{change_counts['created']} archivos creados" if change_counts['created'] > 0 else None,
                        f"{change_counts['modified']} archivos modificados" if change_counts['modified'] > 0 else None,
                        f"{change_counts['deleted']} archivos eliminados" if change_counts['deleted'] > 0 else None
                    ]
                else:  # english
                    summary_lines = [
                        f"{change_counts['created']} files created" if change_counts['created'] > 0 else None,
                        f"{change_counts['modified']} files modified" if change_counts['modified'] > 0 else None,
                        f"{change_counts['deleted']} files deleted" if change_counts['deleted'] > 0 else None
                    ]
                
                # Filtrar líneas vacías
                summary_lines = [line for line in summary_lines if line]
                
                # Añadir resumen al cuerpo
                body_lines.extend(summary_lines)
                
                # Si se solicita análisis de contenido, analizar cada archivo
                if self.analyze_content:
                    body_lines.append("")  # Línea en blanco para separar
                    
                    # Texto según el idioma configurado
                    detailed_changes_text = "Cambios detallados:" if self.language == 'spanish' else "Detailed changes:"
                    body_lines.append(detailed_changes_text)
                    
                    # Analizar cada archivo
                    for file in staged_files:
                        file_analysis = self._analyze_file_changes(repo_path, file['path'], file['event_type'])
                        if file_analysis:
                            body_lines.append(f"- {file['path']}: {file_analysis}")
                
                # Añadir información sobre los tipos de archivos afectados
                file_extensions = {}
                for file in staged_files:
                    ext = os.path.splitext(file['path'])[1]
                    if ext:
                        file_extensions[ext] = file_extensions.get(ext, 0) + 1
                    else:
                        file_extensions['sin extensión'] = file_extensions.get('sin extensión', 0) + 1
                
                # Añadir información sobre tipos de archivos
                if file_extensions:
                    file_types_text = "Tipos de archivos:" if self.language == 'spanish' else "File types:"
                    body_lines.append("")  # Línea en blanco para separar
                    body_lines.append(file_types_text)
                    for ext, count in file_extensions.items():
                        body_lines.append(f"- {ext}: {count}")
            else:
                # Listar todos los archivos con sus tipos de cambio
                for file in staged_files:
                    # Textos según el idioma configurado
                    event_type_texts = {
                        'spanish': {
                            'created': 'creado',
                            'modified': 'modificado',
                            'deleted': 'eliminado'
                        },
                        'english': {
                            'created': 'created',
                            'modified': 'modified',
                            'deleted': 'deleted'
                        }
                    }
                    
                    event_type_text = event_type_texts.get(self.language, event_type_texts['english']).get(
                        file['event_type'], file['event_type'])
                    
                    # Si se solicita análisis de contenido, añadir detalles del análisis
                    if self.analyze_content:
                        file_analysis = self._analyze_file_changes(repo_path, file['path'], file['event_type'])
                        if file_analysis:
                            body_lines.append(f"- {file['path']} ({event_type_text}): {file_analysis}")
                        else:
                            body_lines.append(f"- {file['path']} ({event_type_text})")
                    else:
                        body_lines.append(f"- {file['path']} ({event_type_text})")
            
            body = "\n".join(body_lines)
        
        # Generar el pie de página si está habilitado
        footer = None
        if self.include_footer:
            # Texto según el idioma configurado
            affected_files_text = "Archivos afectados:" if self.language == 'spanish' else "Affected files:"
            footer = f"{affected_files_text} {len(staged_files)}"
        
        # Construir el mensaje completo
        commit_message = self._build_commit_message(title, body, footer)
        
        return {
            'module': 'CommitMessageGenerator',
            'success': True,
            'summary': f"Mensaje de commit generado para {len(staged_files)} archivos en stage",
            'commit_message': commit_message
        }
    
    def _determine_common_scope(self, file_paths):
        """
        Determina un alcance común basado en múltiples rutas de archivos.
        
        Args:
            file_paths (list): Lista de rutas de archivos.
            
        Returns:
            str: Alcance común o None si no hay un alcance común claro.
        """
        if not file_paths:
            return None
            
        # Extraer directorios de primer nivel
        first_level_dirs = set()
        for path in file_paths:
            parts = path.split('/')
            if len(parts) > 1:
                first_level_dirs.add(parts[0])
        
        # Si todos los archivos están en el mismo directorio de primer nivel, usarlo como scope
        if len(first_level_dirs) == 1:
            return first_level_dirs.pop()
            
        # Si hay varios directorios, verificar si todos son del mismo tipo
        if all(dir.startswith('test') for dir in first_level_dirs):
            return 'tests'
        if all(dir.startswith('doc') for dir in first_level_dirs):
            return 'docs'
            
        # Si no hay un patrón claro, devolver None
        return None

    def _analyze_file_changes(self, repo_path, file_path, event_type):
        """
        Analiza los cambios internos de un archivo para generar un resumen.
        
        Args:
            repo_path (str): Ruta del repositorio.
            file_path (str): Ruta del archivo.
            event_type (str): Tipo de evento (created, modified, deleted).
            
        Returns:
            str: Resumen de los cambios internos del archivo.
        """
        try:
            repo = git.Repo(repo_path)
            
            # Si el archivo fue eliminado, no podemos analizar su contenido actual
            if event_type == 'deleted':
                # Obtener el contenido anterior del archivo
                try:
                    old_content = repo.git.show(f'HEAD:{file_path}')
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    # Contar líneas y determinar tipo de archivo
                    line_count = len(old_content.splitlines())
                    
                    # Texto según el idioma configurado
                    if self.language == 'spanish':
                        return f"Archivo eliminado con {line_count} líneas"
                    else:
                        return f"Deleted file with {line_count} lines"
                except git.exc.GitCommandError:
                    # El archivo no existía en HEAD
                    if self.language == 'spanish':
                        return "Archivo eliminado (no existía en HEAD)"
                    else:
                        return "Deleted file (did not exist in HEAD)"
            
            # Si el archivo fue creado, analizamos su contenido actual
            elif event_type == 'created':
                file_path_full = os.path.join(repo_path, file_path)
                if os.path.exists(file_path_full):
                    with open(file_path_full, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    line_count = len(content.splitlines())
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    # Detectar tipo de contenido según la extensión
                    content_type = self._detect_content_type(file_ext, content)
                    
                    # Texto según el idioma configurado
                    if self.language == 'spanish':
                        return f"Nuevo archivo con {line_count} líneas ({content_type})"
                    else:
                        return f"New file with {line_count} lines ({content_type})"
                else:
                    if self.language == 'spanish':
                        return "Nuevo archivo (no encontrado en el sistema de archivos)"
                    else:
                        return "New file (not found in filesystem)"
            
            # Si el archivo fue modificado, comparamos su contenido anterior y actual
            elif event_type == 'modified':
                try:
                    # Obtener el diff del archivo
                    diff = repo.git.diff('HEAD', '--', file_path)
                    
                    # Contar líneas añadidas y eliminadas
                    added_lines = 0
                    removed_lines = 0
                    
                    for line in diff.splitlines():
                        if line.startswith('+') and not line.startswith('+++'):
                            added_lines += 1
                        elif line.startswith('-') and not line.startswith('---'):
                            removed_lines += 1
                    
                    # Texto según el idioma configurado
                    if self.language == 'spanish':
                        return f"Modificado: {added_lines} líneas añadidas, {removed_lines} líneas eliminadas"
                    else:
                        return f"Modified: {added_lines} lines added, {removed_lines} lines removed"
                except git.exc.GitCommandError as e:
                    logger.error(f"Error al obtener diff: {e}")
                    if self.language == 'spanish':
                        return "Archivo modificado (error al analizar cambios)"
                    else:
                        return "Modified file (error analyzing changes)"
            
            return None
        except Exception as e:
            logger.error(f"Error al analizar cambios del archivo {file_path}: {e}")
            return None
    
    def _detect_content_type(self, file_ext, content):
        """
        Detecta el tipo de contenido de un archivo basado en su extensión y contenido.
        
        Args:
            file_ext (str): Extensión del archivo.
            content (str): Contenido del archivo.
            
        Returns:
            str: Tipo de contenido detectado.
        """
        # Mapeo de extensiones a tipos de contenido
        ext_to_type = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.html': 'HTML',
            '.css': 'CSS',
            '.json': 'JSON',
            '.md': 'Markdown',
            '.txt': 'texto',
            '.yml': 'YAML',
            '.yaml': 'YAML',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.h': 'C/C++ header',
            '.sh': 'Shell script',
            '.bat': 'Batch script',
            '.ps1': 'PowerShell script'
        }
        
        # Detectar tipo por extensión
        content_type = ext_to_type.get(file_ext.lower(), 'archivo')
        
        # Si no se pudo detectar por extensión, intentar detectar por contenido
        if content_type == 'archivo' and content:
            # Detectar si es código fuente
            code_patterns = [
                (r'function\s+\w+\s*\(', 'JavaScript'),
                (r'def\s+\w+\s*\(', 'Python'),
                (r'class\s+\w+', 'código'),
                (r'import\s+\w+', 'código'),
                (r'<html', 'HTML'),
                (r'<body', 'HTML'),
                (r'<div', 'HTML'),
                (r'#include', 'C/C++')
            ]
            
            for pattern, detected_type in code_patterns:
                if re.search(pattern, content):
                    content_type = detected_type
                    break
        
        return content_type
