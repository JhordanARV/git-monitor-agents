import os
import json
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestiona la configuración del sistema y los módulos."""
    
    def __init__(self, config_path=None):
        """
        Inicializa el gestor de configuración.
        
        Args:
            config_path (str, opcional): Ruta al archivo de configuración. Por defecto usa la variable
                                         de entorno GIT_MONITOR_CONFIG o 'config.yaml'.
        """
        self.config_path = config_path or os.environ.get('GIT_MONITOR_CONFIG', 'config.yaml')
        self._config = self._load_config()
        logger.info(f"Configuración cargada desde: {self.config_path}")
    
    def _load_config(self):
        """
        Carga la configuración desde el archivo.
        
        Returns:
            dict: Configuración cargada o configuración por defecto si hay error.
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
            return self._create_default_config()
            
        ext = os.path.splitext(self.config_path)[1].lower()
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if ext == '.json':
                    return json.load(f)
                elif ext in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                else:
                    # Formato no soportado, usar valores predeterminados
                    logger.warning(f"Formato de configuración no soportado: {ext}")
                    return self._create_default_config()
        except Exception as e:
            logger.error(f"Error al cargar configuración: {e}")
            return self._create_default_config()
    
    def _create_default_config(self):
        """
        Crea una configuración predeterminada.
        
        Returns:
            dict: Configuración predeterminada.
        """
        default_config = {
            'core': {
                'repo_path': os.environ.get('REPO_PATH', '.'),
                'branch': os.environ.get('REPO_BRANCH', 'main'),
                'poll_interval': 300,  # 5 minutos
                'ai_provider': os.environ.get('AI_PROVIDER', 'openai')
            },
            'modules': {
                # La configuración de módulos se agregará dinámicamente
            }
        }
        
        logger.info("Creando configuración predeterminada")
        return default_config
    
    def get_config(self):
        """
        Obtiene la configuración actual.
        
        Returns:
            dict: Configuración actual.
        """
        return self._config
    
    def get_module_config(self, module_name):
        """
        Obtiene la configuración para un módulo específico.
        
        Args:
            module_name (str): Nombre del módulo.
            
        Returns:
            dict: Configuración del módulo o diccionario vacío si no existe.
        """
        return self._config.get('modules', {}).get(module_name, {})
    
    def update_config(self, new_config):
        """
        Actualiza la configuración y la guarda.
        
        Args:
            new_config (dict): Nueva configuración a aplicar.
            
        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        try:
            self._config.update(new_config)
            self._save_config()
            logger.info("Configuración actualizada correctamente")
            return True
        except Exception as e:
            logger.error(f"Error al actualizar configuración: {e}")
            return False
        
    def _save_config(self):
        """
        Guarda la configuración en el archivo.
        
        Raises:
            Exception: Si hay un error al guardar la configuración.
        """
        ext = os.path.splitext(self.config_path)[1].lower()
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                if ext == '.json':
                    json.dump(self._config, f, indent=2)
                elif ext in ['.yaml', '.yml']:
                    yaml.dump(self._config, f)
                else:
                    # Usar YAML por defecto
                    config_path = f"{os.path.splitext(self.config_path)[0]}.yaml"
                    with open(config_path, 'w', encoding='utf-8') as f:
                        yaml.dump(self._config, f)
                        self.config_path = config_path
            logger.info(f"Configuración guardada en: {self.config_path}")
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            raise
