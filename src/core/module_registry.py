import logging

logger = logging.getLogger(__name__)

class ModuleRegistry:
    """Registro central de módulos disponibles."""
    
    _modules = {}
    
    @classmethod
    def register(cls, module_class):
        """
        Registra un nuevo tipo de módulo.
        
        Args:
            module_class (class): Clase del módulo a registrar.
            
        Returns:
            class: La misma clase que se pasó como argumento (para usar como decorador).
        """
        cls._modules[module_class.__name__] = module_class
        logger.debug(f"Módulo registrado: {module_class.__name__}")
        return module_class
    
    @classmethod
    def get_module(cls, name):
        """
        Obtiene una clase de módulo por nombre.
        
        Args:
            name (str): Nombre del módulo a obtener.
            
        Returns:
            class: Clase del módulo, o None si no existe.
        """
        return cls._modules.get(name)
    
    @classmethod
    def get_all_modules(cls):
        """
        Devuelve todos los módulos registrados.
        
        Returns:
            dict: Diccionario con los nombres de los módulos como claves y las clases como valores.
        """
        return cls._modules
        
    @classmethod
    def create_module_instance(cls, name, config=None):
        """
        Crea una instancia de un módulo por nombre.
        
        Args:
            name (str): Nombre del módulo a instanciar.
            config (dict, opcional): Configuración para el módulo. Por defecto es None.
            
        Returns:
            object: Instancia del módulo, o None si no existe.
            
        Raises:
            ValueError: Si el módulo no existe.
        """
        module_class = cls.get_module(name)
        if not module_class:
            raise ValueError(f"El módulo '{name}' no está registrado")
        
        return module_class(config)
