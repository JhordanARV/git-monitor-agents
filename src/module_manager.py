import logging
import importlib
import pkgutil
import os
from src.core.module_registry import ModuleRegistry
from src.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ModuleManager:
    """Gestiona la carga y ejecución de módulos."""
    
    def __init__(self, config_path=None):
        """
        Inicializa el gestor de módulos.
        
        Args:
            config_path (str, opcional): Ruta al archivo de configuración.
        """
        self.config_manager = ConfigManager(config_path)
        self.modules = {}
        self._discover_and_register_modules()
        self._initialize_modules()
        
    def _discover_and_register_modules(self):
        """Descubre y registra automáticamente todos los módulos disponibles."""
        logger.info("Descubriendo módulos...")
        
        # Importar todos los módulos en el paquete modules
        modules_path = os.path.join(os.path.dirname(__file__), 'modules')
        
        # Recorrer todos los subdirectorios en modules
        for _, module_name, is_pkg in pkgutil.iter_modules([modules_path]):
            if is_pkg:
                # Es un paquete, buscar módulos dentro
                submodule_path = os.path.join(modules_path, module_name)
                for _, submodule_name, _ in pkgutil.iter_modules([submodule_path]):
                    try:
                        # Importar el módulo
                        full_module_name = f"src.modules.{module_name}.{submodule_name}"
                        importlib.import_module(full_module_name)
                        logger.debug(f"Módulo importado: {full_module_name}")
                    except Exception as e:
                        logger.error(f"Error al importar módulo {full_module_name}: {e}")
        
        logger.info(f"Módulos registrados: {list(ModuleRegistry.get_all_modules().keys())}")
        
    def _initialize_modules(self):
        """Inicializa las instancias de los módulos según la configuración."""
        logger.info("Inicializando módulos...")
        
        for module_name, module_class in ModuleRegistry.get_all_modules().items():
            try:
                # Obtener configuración del módulo
                module_config = self.config_manager.get_module_config(module_name)
                
                # Crear instancia del módulo
                module_instance = module_class(module_config)
                self.modules[module_name] = module_instance
                
                logger.info(f"Módulo inicializado: {module_name} (enabled={module_instance.is_enabled()})")
            except Exception as e:
                logger.error(f"Error al inicializar módulo {module_name}: {e}")
                
    def process_event(self, event_data):
        """
        Procesa un evento a través de todos los módulos habilitados.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            list: Lista de resultados de procesamiento de cada módulo.
        """
        results = []
        
        for name, module in self.modules.items():
            if module.is_enabled():
                try:
                    logger.debug(f"Procesando evento con módulo {name}")
                    result = module.process(event_data)
                    if result:
                        results.append(result)
                        logger.debug(f"Módulo {name} generó resultado: {result}")
                except Exception as e:
                    logger.error(f"Error al procesar evento con módulo {name}: {e}")
            else:
                logger.debug(f"Módulo {name} deshabilitado, ignorando evento")
                
        return results
        
    def get_module(self, name):
        """
        Obtiene una instancia de módulo por nombre.
        
        Args:
            name (str): Nombre del módulo.
            
        Returns:
            object: Instancia del módulo, o None si no existe.
        """
        return self.modules.get(name)
        
    def get_all_modules(self):
        """
        Devuelve todas las instancias de módulos.
        
        Returns:
            dict: Diccionario con los nombres de los módulos como claves y las instancias como valores.
        """
        return self.modules
