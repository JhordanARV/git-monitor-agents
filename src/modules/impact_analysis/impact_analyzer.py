import os
import re
import logging
from src.core.base_module import BaseModule
from src.core.module_registry import ModuleRegistry

logger = logging.getLogger(__name__)

@ModuleRegistry.register
class ImpactAnalyzer(BaseModule):
    """Analiza el impacto potencial de los cambios en el código."""
    
    def __init__(self, config=None):
        """
        Inicializa el analizador de impacto.
        
        Args:
            config (dict, opcional): Configuración del módulo. Por defecto es None.
        """
        super().__init__(config)
        self.risk_threshold = self.config.get('risk_threshold', 'medium')
        self.analyze_dependencies = self.config.get('analyze_dependencies', True)
        self.suggest_tests = self.config.get('suggest_tests', True)
        
    def process(self, event_data):
        """
        Procesa un evento de cambio y analiza su impacto potencial.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            dict: Resultado del análisis de impacto.
        """
        if not self.is_enabled():
            logger.debug(f"Módulo {self.name} deshabilitado, ignorando evento")
            return None
            
        if event_data['type'] not in ['file_change', 'commit']:
            logger.debug(f"Evento ignorado por {self.name}: no es un cambio relevante")
            return None
            
        # Para commits, analizar todos los archivos modificados
        if event_data['type'] == 'commit':
            files = event_data.get('files', [])
            if not files:
                logger.warning(f"Commit sin archivos modificados, ignorando")
                return None
                
            # Análisis de impacto para cada archivo en el commit
            impacts = []
            for file_path in files:
                file_impact = self._analyze_file_impact(file_path, event_data.get('repo_path', '.'))
                if file_impact:
                    impacts.append(file_impact)
                    
            if not impacts:
                logger.info(f"No se encontró impacto significativo en los archivos del commit")
                return {
                    'module': self.name,
                    'type': 'commit',
                    'id': event_data.get('id', ''),
                    'impact_level': 'low',
                    'summary': 'No se detectó impacto significativo'
                }
                
            # Determinar el nivel de impacto general
            impact_level = self._determine_overall_impact(impacts)
            
            return {
                'module': self.name,
                'type': 'commit',
                'id': event_data.get('id', ''),
                'impact_level': impact_level,
                'file_impacts': impacts,
                'summary': f'Impacto {impact_level} detectado en {len(impacts)} archivos'
            }
        
        # Para cambios de archivo individuales
        file_path = event_data.get('path')
        if not file_path:
            logger.warning(f"Evento sin ruta de archivo, ignorando")
            return None
            
        # Analizar el impacto del cambio en el archivo
        impact = self._analyze_file_impact(file_path, event_data.get('repo_path', '.'))
        if not impact:
            logger.info(f"No se encontró impacto significativo en {file_path}")
            return {
                'module': self.name,
                'type': 'file_change',
                'file': file_path,
                'impact_level': 'low',
                'summary': 'No se detectó impacto significativo'
            }
            
        return {
            'module': self.name,
            'type': 'file_change',
            'file': file_path,
            'impact_level': impact['impact_level'],
            'affected_components': impact.get('affected_components', []),
            'suggested_tests': impact.get('suggested_tests', []),
            'summary': impact.get('summary', 'Análisis de impacto completado')
        }
    
    def _analyze_file_impact(self, file_path, repo_path):
        """
        Analiza el impacto de cambios en un archivo específico.
        
        Args:
            file_path (str): Ruta del archivo a analizar.
            repo_path (str): Ruta base del repositorio.
            
        Returns:
            dict: Información sobre el impacto del cambio.
        """
        # Determinar el tipo de archivo
        ext = os.path.splitext(file_path)[1].lower()
        
        # Evaluar la criticidad del archivo
        criticality = self._evaluate_file_criticality(file_path)
        
        # Identificar componentes potencialmente afectados
        affected_components = []
        if self.analyze_dependencies:
            affected_components = self._identify_affected_components(file_path, repo_path)
            
        # Sugerir pruebas relevantes
        suggested_tests = []
        if self.suggest_tests:
            suggested_tests = self._suggest_relevant_tests(file_path, repo_path)
            
        # Determinar nivel de impacto
        impact_level = self._calculate_impact_level(criticality, len(affected_components))
        
        # Generar resumen
        summary = f"Cambios en {file_path} tienen un impacto {impact_level}"
        if affected_components:
            summary += f" y podrían afectar {len(affected_components)} componentes"
            
        return {
            'file': file_path,
            'criticality': criticality,
            'impact_level': impact_level,
            'affected_components': affected_components,
            'suggested_tests': suggested_tests,
            'summary': summary
        }
    
    def _evaluate_file_criticality(self, file_path):
        """
        Evalúa la criticidad de un archivo basado en su nombre y ubicación.
        
        Args:
            file_path (str): Ruta del archivo.
            
        Returns:
            str: Nivel de criticidad ('high', 'medium', 'low').
        """
        # Patrones que indican alta criticidad
        high_criticality_patterns = [
            r'security', r'auth', r'password', r'credential', r'token',
            r'payment', r'core', r'config', r'main', r'database', r'db',
            r'api', r'server', r'router', r'controller'
        ]
        
        # Patrones que indican criticidad media
        medium_criticality_patterns = [
            r'service', r'model', r'store', r'state', r'util', r'helper',
            r'middleware', r'validator', r'parser', r'formatter'
        ]
        
        # Verificar patrones de alta criticidad
        for pattern in high_criticality_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return 'high'
                
        # Verificar patrones de criticidad media
        for pattern in medium_criticality_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return 'medium'
                
        # Por defecto, criticidad baja
        return 'low'
    
    def _identify_affected_components(self, file_path, repo_path):
        """
        Identifica componentes que podrían verse afectados por cambios en el archivo.
        
        Args:
            file_path (str): Ruta del archivo modificado.
            repo_path (str): Ruta base del repositorio.
            
        Returns:
            list: Lista de componentes potencialmente afectados.
        """
        # En una implementación real, aquí se analizaría el código para encontrar dependencias
        # Por ahora, devolvemos un ejemplo
        
        # Extraer el nombre base del archivo sin extensión
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Componentes de ejemplo que podrían verse afectados
        affected = []
        
        # Si es un archivo de modelo, los controladores podrían verse afectados
        if 'model' in file_path:
            affected.append({
                'type': 'controller',
                'name': f"{base_name}_controller",
                'reason': f"Utiliza el modelo {base_name}"
            })
            
        # Si es un archivo de servicio, las vistas podrían verse afectadas
        if 'service' in file_path:
            affected.append({
                'type': 'view',
                'name': f"{base_name}_view",
                'reason': f"Consume el servicio {base_name}"
            })
            
        # Si es un archivo de utilidad, múltiples componentes podrían verse afectados
        if 'util' in file_path or 'helper' in file_path:
            affected.append({
                'type': 'multiple',
                'name': "varios_componentes",
                'reason': f"Dependen de la utilidad {base_name}"
            })
            
        return affected
    
    def _suggest_relevant_tests(self, file_path, repo_path):
        """
        Sugiere pruebas relevantes para validar los cambios en el archivo.
        
        Args:
            file_path (str): Ruta del archivo modificado.
            repo_path (str): Ruta base del repositorio.
            
        Returns:
            list: Lista de pruebas sugeridas.
        """
        # En una implementación real, aquí se analizaría el código y se buscarían pruebas existentes
        # Por ahora, devolvemos sugerencias de ejemplo
        
        # Extraer el nombre base del archivo sin extensión
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Pruebas sugeridas
        suggested = []
        
        # Prueba unitaria para el componente modificado
        suggested.append({
            'type': 'unit',
            'name': f"test_{base_name}",
            'description': f"Pruebas unitarias para {base_name}"
        })
        
        # Si es un componente crítico, sugerir pruebas de integración
        if self._evaluate_file_criticality(file_path) in ['high', 'medium']:
            suggested.append({
                'type': 'integration',
                'name': f"integration_test_{base_name}",
                'description': f"Pruebas de integración que involucran {base_name}"
            })
            
        # Si es un componente de interfaz, sugerir pruebas de UI
        if 'view' in file_path or 'component' in file_path:
            suggested.append({
                'type': 'ui',
                'name': f"ui_test_{base_name}",
                'description': f"Pruebas de interfaz para {base_name}"
            })
            
        return suggested
    
    def _calculate_impact_level(self, criticality, affected_count):
        """
        Calcula el nivel de impacto basado en la criticidad y componentes afectados.
        
        Args:
            criticality (str): Nivel de criticidad del archivo.
            affected_count (int): Número de componentes afectados.
            
        Returns:
            str: Nivel de impacto ('high', 'medium', 'low').
        """
        # Alta criticidad siempre tiene al menos impacto medio
        if criticality == 'high':
            return 'high' if affected_count > 0 else 'medium'
            
        # Criticidad media puede tener impacto alto si afecta muchos componentes
        if criticality == 'medium':
            return 'high' if affected_count > 2 else 'medium'
            
        # Baja criticidad solo tiene impacto alto si afecta muchos componentes
        return 'high' if affected_count > 4 else 'medium' if affected_count > 0 else 'low'
    
    def _determine_overall_impact(self, impacts):
        """
        Determina el nivel de impacto general basado en múltiples impactos.
        
        Args:
            impacts (list): Lista de impactos individuales.
            
        Returns:
            str: Nivel de impacto general ('high', 'medium', 'low').
        """
        # Si hay algún impacto alto, el impacto general es alto
        if any(impact['impact_level'] == 'high' for impact in impacts):
            return 'high'
            
        # Si hay algún impacto medio, el impacto general es medio
        if any(impact['impact_level'] == 'medium' for impact in impacts):
            return 'medium'
            
        # Si todos los impactos son bajos, el impacto general es bajo
        return 'low'
    
    @classmethod
    def get_config_schema(cls):
        """
        Devuelve el esquema de configuración para este módulo.
        
        Returns:
            dict: Esquema de configuración.
        """
        return {
            'risk_threshold': {
                'type': 'string',
                'enum': ['high', 'medium', 'low'],
                'default': 'medium',
                'description': 'Umbral de riesgo para notificaciones'
            },
            'analyze_dependencies': {
                'type': 'boolean',
                'default': True,
                'description': 'Analizar dependencias entre componentes'
            },
            'suggest_tests': {
                'type': 'boolean',
                'default': True,
                'description': 'Sugerir pruebas relevantes para los cambios'
            },
            'enabled': {
                'type': 'boolean',
                'default': True,
                'description': 'Activar/desactivar este módulo'
            }
        }
