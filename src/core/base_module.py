from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseModule(ABC):
    """Clase base para todos los módulos de Git-Monitor."""
    
    def __init__(self, config=None):
        """
        Inicializa un módulo base.
        
        Args:
            config (dict, opcional): Configuración del módulo. Por defecto es None.
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        logger.debug(f"Inicializando módulo {self.name} (enabled={self.enabled})")
        
    @abstractmethod
    def process(self, event_data):
        """
        Procesa un evento y devuelve resultados.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            dict: Resultado del procesamiento.
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls):
        """
        Devuelve el esquema de configuración para este módulo.
        
        Returns:
            dict: Esquema de configuración en formato similar a JSON Schema.
        """
        pass
    
    @property
    def name(self):
        """Nombre del módulo."""
        return self.__class__.__name__
    
    @property
    def description(self):
        """Descripción del módulo."""
        return self.__doc__
        
    def is_enabled(self):
        """
        Verifica si el módulo está habilitado.
        
        Returns:
            bool: True si el módulo está habilitado, False en caso contrario.
        """
        return self.enabled
