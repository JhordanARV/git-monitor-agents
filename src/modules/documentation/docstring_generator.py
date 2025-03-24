import os
import re
import logging
from src.core.base_module import BaseModule
from src.core.module_registry import ModuleRegistry

logger = logging.getLogger(__name__)

@ModuleRegistry.register
class DocstringGenerator(BaseModule):
    """Genera y actualiza docstrings para código sin documentar."""
    
    def __init__(self, config=None):
        """
        Inicializa el generador de docstrings.
        
        Args:
            config (dict, opcional): Configuración del módulo. Por defecto es None.
        """
        super().__init__(config)
        self.doc_format = self.config.get('format', 'google')
        self.target_langs = self.config.get('languages', ['python', 'javascript'])
        self.llm = None  # Se inicializará bajo demanda
        
    def process(self, event_data):
        """
        Procesa un evento de cambio de archivo y genera docstrings si es necesario.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            dict: Resultado del procesamiento con información sobre los docstrings generados.
        """
        if not self.is_enabled():
            logger.debug(f"Módulo {self.name} deshabilitado, ignorando evento")
            return None
            
        if event_data['type'] != 'file_change':
            logger.debug(f"Evento ignorado por {self.name}: no es un cambio de archivo")
            return None
            
        file_path = event_data.get('path')
        if not file_path:
            logger.warning(f"Evento sin ruta de archivo, ignorando")
            return None
            
        # Verificar si el archivo es de un lenguaje soportado
        file_ext = os.path.splitext(file_path)[1].lower()
        lang = self._get_language_from_extension(file_ext)
        if not lang or lang not in self.target_langs:
            logger.debug(f"Archivo {file_path} no es de un lenguaje soportado ({lang})")
            return None
            
        # Obtener el contenido del archivo
        content = event_data.get('content', '')
        if not content:
            logger.warning(f"No hay contenido para analizar en {file_path}")
            return None
            
        # Analizar el archivo para encontrar funciones/clases sin docstrings
        missing_docs = self._find_missing_docstrings(content, lang)
        if not missing_docs:
            logger.info(f"No se encontraron funciones/clases sin documentar en {file_path}")
            return {
                'module': self.name,
                'file': file_path,
                'missing_docs': 0,
                'generated_docs': 0,
                'summary': 'No se encontraron elementos sin documentar'
            }
            
        # Generar docstrings para las funciones/clases sin documentar
        generated_docs = self._generate_docstrings(content, missing_docs, lang)
        
        return {
            'module': self.name,
            'file': file_path,
            'missing_docs': len(missing_docs),
            'generated_docs': len(generated_docs),
            'summary': f'Se generaron {len(generated_docs)} docstrings para {file_path}',
            'docstrings': generated_docs
        }
    
    def _get_language_from_extension(self, ext):
        """
        Determina el lenguaje de programación basado en la extensión del archivo.
        
        Args:
            ext (str): Extensión del archivo (con el punto).
            
        Returns:
            str: Lenguaje de programación o None si no es reconocido.
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go'
        }
        return ext_map.get(ext)
    
    def _find_missing_docstrings(self, content, lang):
        """
        Encuentra funciones y clases sin docstrings en el contenido.
        
        Args:
            content (str): Contenido del archivo.
            lang (str): Lenguaje de programación.
            
        Returns:
            list: Lista de diccionarios con información sobre las funciones/clases sin docstrings.
        """
        missing_docs = []
        
        if lang == 'python':
            # Buscar funciones y clases en Python
            function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\):'
            class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\((.*?)\))?:'
            
            # Encontrar funciones
            for match in re.finditer(function_pattern, content):
                name = match.group(1)
                params = match.group(2)
                start_pos = match.start()
                
                # Verificar si ya tiene docstring
                next_lines = content[match.end():match.end() + 200]
                if not re.search(r'^\s*"""', next_lines.lstrip(), re.MULTILINE):
                    # Extraer el cuerpo de la función para análisis
                    function_body = self._extract_function_body(content, match.end())
                    
                    missing_docs.append({
                        'type': 'function',
                        'name': name,
                        'params': params,
                        'position': start_pos,
                        'body': function_body
                    })
            
            # Encontrar clases
            for match in re.finditer(class_pattern, content):
                name = match.group(1)
                inheritance = match.group(2) or ''
                start_pos = match.start()
                
                # Verificar si ya tiene docstring
                next_lines = content[match.end():match.end() + 200]
                if not re.search(r'^\s*"""', next_lines.lstrip(), re.MULTILINE):
                    missing_docs.append({
                        'type': 'class',
                        'name': name,
                        'inheritance': inheritance,
                        'position': start_pos
                    })
        
        elif lang in ['javascript', 'typescript']:
            # Implementar para JavaScript/TypeScript
            # (Simplificado para este ejemplo)
            function_pattern = r'(?:function|const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=?\s*(?:function)?\s*\((.*?)\)'
            class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:extends\s+([a-zA-Z_][a-zA-Z0-9_]*))?'
            
            # Lógica similar a Python...
        
        return missing_docs
    
    def _extract_function_body(self, content, start_pos):
        """
        Extrae el cuerpo de una función para análisis.
        
        Args:
            content (str): Contenido del archivo.
            start_pos (int): Posición de inicio después de la definición de la función.
            
        Returns:
            str: Cuerpo de la función.
        """
        # Implementación simplificada
        lines = content[start_pos:start_pos + 500].split('\n')
        body_lines = []
        indent = None
        
        for line in lines[1:]:  # Saltar la primera línea (def ...)
            if not line.strip():
                continue
                
            # Determinar la indentación base
            if indent is None:
                match = re.match(r'^(\s+)', line)
                if match:
                    indent = len(match.group(1))
                else:
                    continue
            
            # Si encontramos una línea con menor indentación, hemos salido de la función
            curr_indent = len(re.match(r'^(\s*)', line).group(1))
            if curr_indent < indent:
                break
                
            body_lines.append(line)
            
            # Limitar a 10 líneas para el análisis
            if len(body_lines) >= 10:
                break
                
        return '\n'.join(body_lines)
    
    def _generate_docstrings(self, content, missing_docs, lang):
        """
        Genera docstrings para las funciones/clases sin documentar.
        
        Args:
            content (str): Contenido del archivo.
            missing_docs (list): Lista de funciones/clases sin documentar.
            lang (str): Lenguaje de programación.
            
        Returns:
            list: Lista de docstrings generados.
        """
        # En una implementación real, aquí se usaría el LLM para generar los docstrings
        # Por ahora, generamos docstrings de ejemplo
        generated = []
        
        for item in missing_docs:
            if item['type'] == 'function':
                docstring = self._generate_function_docstring(item, lang)
                generated.append({
                    'type': 'function',
                    'name': item['name'],
                    'docstring': docstring
                })
            elif item['type'] == 'class':
                docstring = self._generate_class_docstring(item, lang)
                generated.append({
                    'type': 'class',
                    'name': item['name'],
                    'docstring': docstring
                })
                
        return generated
    
    def _generate_function_docstring(self, func_info, lang):
        """
        Genera un docstring para una función.
        
        Args:
            func_info (dict): Información sobre la función.
            lang (str): Lenguaje de programación.
            
        Returns:
            str: Docstring generado.
        """
        # Implementación de ejemplo (en una versión real se usaría IA)
        params = func_info['params'].split(',')
        param_docs = ""
        
        for param in params:
            param = param.strip()
            if param:
                param_name = param.split(':')[0].split('=')[0].strip()
                if param_name:
                    param_docs += f"        {param_name}: Descripción del parámetro.\n"
        
        if self.doc_format == 'google':
            docstring = f'"""\n    Descripción de la función {func_info["name"]}.\n    \n'
            if param_docs:
                docstring += f"    Args:\n{param_docs}\n"
            docstring += f"    Returns:\n        Descripción del valor de retorno.\n    \"\"\""
        else:
            # Otros formatos...
            docstring = f'"""\n    Descripción de la función {func_info["name"]}.\n    """'
            
        return docstring
    
    def _generate_class_docstring(self, class_info, lang):
        """
        Genera un docstring para una clase.
        
        Args:
            class_info (dict): Información sobre la clase.
            lang (str): Lenguaje de programación.
            
        Returns:
            str: Docstring generado.
        """
        # Implementación de ejemplo
        if self.doc_format == 'google':
            docstring = f'"""\n    Clase {class_info["name"]}.\n    \n'
            if class_info.get('inheritance'):
                docstring += f"    Hereda de: {class_info['inheritance']}\n    \n"
            docstring += f"    Attributes:\n        Atributos de la clase.\n    \"\"\""
        else:
            # Otros formatos...
            docstring = f'"""\n    Clase {class_info["name"]}.\n    """'
            
        return docstring
    
    @classmethod
    def get_config_schema(cls):
        """
        Devuelve el esquema de configuración para este módulo.
        
        Returns:
            dict: Esquema de configuración.
        """
        return {
            'format': {
                'type': 'string',
                'enum': ['google', 'numpy', 'sphinx'],
                'default': 'google',
                'description': 'Formato de docstring a generar'
            },
            'languages': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': ['python', 'javascript'],
                'description': 'Lenguajes para los que generar docstrings'
            },
            'enabled': {
                'type': 'boolean',
                'default': True,
                'description': 'Activar/desactivar este módulo'
            }
        }
