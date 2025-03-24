"""
Módulo para generar mensajes de commit automáticamente basados en los cambios.
"""

import os
import logging
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
        self.max_length = self.config.get('max_length', 72)
        
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
