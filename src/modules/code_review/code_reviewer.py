import os
import re
import logging
from src.core.base_module import BaseModule
from src.core.module_registry import ModuleRegistry
from src.utils.ai_provider import AIProvider

logger = logging.getLogger(__name__)

@ModuleRegistry.register
class CodeReviewer(BaseModule):
    """Revisa automáticamente el código y proporciona sugerencias de mejora."""
    
    def __init__(self, config=None):
        """
        Inicializa el revisor de código.
        
        Args:
            config (dict, opcional): Configuración del módulo. Por defecto es None.
        """
        super().__init__(config)
        self.review_types = self.config.get('review_types', ['quality', 'security', 'performance'])
        self.suggest_fixes = self.config.get('suggest_fixes', True)
        self.severity_threshold = self.config.get('severity_threshold', 'low')
        self.use_ai = self.config.get('use_ai', False)
        
        # Inicializar LLM si se va a usar IA
        if self.use_ai and self.is_enabled():
            try:
                self.llm = AIProvider.get_llm(self.config)
                logger.info(f"LLM inicializado para {self.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error al inicializar LLM: {e}")
                self.llm = None
        
    def process(self, event_data):
        """
        Procesa un evento de cambio y realiza una revisión de código.
        
        Args:
            event_data (dict): Datos del evento a procesar.
            
        Returns:
            dict: Resultado de la revisión de código.
        """
        if not self.is_enabled():
            logger.debug(f"Módulo {self.name} deshabilitado, ignorando evento")
            return None
            
        if event_data['type'] not in ['file_change', 'commit']:
            logger.debug(f"Evento ignorado por {self.name}: no es un cambio relevante")
            return None
            
        # Para commits, revisar todos los archivos modificados
        if event_data['type'] == 'commit':
            files = event_data.get('files', [])
            if not files:
                logger.warning(f"Commit sin archivos modificados, ignorando")
                return None
                
            # Revisión de código para cada archivo en el commit
            reviews = []
            for file_path in files:
                file_review = self._review_file(file_path, event_data.get('repo_path', '.'))
                if file_review and file_review.get('issues'):
                    reviews.append(file_review)
                    
            if not reviews:
                logger.info(f"No se encontraron problemas en los archivos del commit")
                return {
                    'module': self.name,
                    'type': 'commit',
                    'id': event_data.get('id', ''),
                    'issues_found': 0,
                    'summary': 'No se detectaron problemas'
                }
                
            # Contar el total de problemas
            total_issues = sum(len(review.get('issues', [])) for review in reviews)
            
            return {
                'module': self.name,
                'type': 'commit',
                'id': event_data.get('id', ''),
                'issues_found': total_issues,
                'file_reviews': reviews,
                'summary': f'Se encontraron {total_issues} problemas en {len(reviews)} archivos'
            }
        
        # Para cambios de archivo individuales
        file_path = event_data.get('path')
        if not file_path:
            logger.warning(f"Evento sin ruta de archivo, ignorando")
            return None
            
        # Revisar el archivo
        review = self._review_file(file_path, event_data.get('repo_path', '.'), event_data.get('content', ''))
        if not review or not review.get('issues'):
            logger.info(f"No se encontraron problemas en {file_path}")
            return {
                'module': self.name,
                'type': 'file_change',
                'file': file_path,
                'issues_found': 0,
                'summary': 'No se detectaron problemas'
            }
            
        return {
            'module': self.name,
            'type': 'file_change',
            'file': file_path,
            'issues_found': len(review.get('issues', [])),
            'issues': review.get('issues', []),
            'summary': f'Se encontraron {len(review.get("issues", []))} problemas en {file_path}'
        }
    
    def _review_file(self, file_path, repo_path, content=None, event_type='modified'):
        """
        Revisa un archivo y genera sugerencias.
        
        Args:
            file_path (str): Ruta del archivo a revisar.
            repo_path (str): Ruta base del repositorio.
            content (str, opcional): Contenido del archivo. Si es None, se intentará leer del disco.
            event_type (str): Tipo de evento (created, modified, deleted).
            
        Returns:
            dict: Resultado de la revisión.
        """
        if not content or event_type == 'deleted':
            return None
            
        # Si está habilitada la IA, usarla para la revisión
        if self.use_ai and hasattr(self, 'llm') and self.llm:
            return self._review_file_with_ai(file_path, content, event_type)
            
        # Revisión basada en reglas si no se usa IA
        file_ext = os.path.splitext(file_path)[1].lower()
        
        issues = []
        
        # Revisión de calidad
        if 'quality' in self.review_types:
            quality_issues = self._check_code_quality(content, file_ext)
            issues.extend(quality_issues)
            
        # Revisión de seguridad
        if 'security' in self.review_types:
            security_issues = self._check_security_issues(content, file_ext)
            issues.extend(security_issues)
            
        # Revisión de rendimiento
        if 'performance' in self.review_types:
            performance_issues = self._check_performance_issues(content, file_ext)
            issues.extend(performance_issues)
            
        # Filtrar por severidad
        severity_levels = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1,
            'info': 0
        }
        threshold = severity_levels.get(self.severity_threshold, 0)
        filtered_issues = [issue for issue in issues 
                          if severity_levels.get(issue['severity'], 0) >= threshold]
        
        return {
            'file': file_path,
            'issues': filtered_issues,
            'summary': self._generate_review_summary(filtered_issues)
        }
        
    def _review_file_with_ai(self, file_path, content, event_type='modified'):
        """
        Revisa un archivo utilizando IA y genera sugerencias.
        
        Args:
            file_path (str): Ruta del archivo a revisar.
            content (str): Contenido del archivo.
            event_type (str): Tipo de evento (created, modified, deleted).
            
        Returns:
            dict: Resultado de la revisión con IA.
        """
        try:
            # Determinar el tipo de archivo
            file_ext = os.path.splitext(file_path)[1].lower()
            file_type = self._get_file_type(file_ext)
            
            # Limitar el contenido si es muy grande
            max_content_length = 10000  # Aproximadamente 10KB
            if len(content) > max_content_length:
                content_preview = content[:max_content_length//2] + "\n...\n" + content[-max_content_length//2:]
                content_truncated = True
            else:
                content_preview = content
                content_truncated = False
            
            # Crear el prompt para la IA
            prompt = f"""
            Realiza una revisión de código para el siguiente archivo:
            
            Archivo: {file_path}
            Tipo: {file_type}
            Evento: {event_type}
            
            {f"NOTA: El contenido es muy grande y ha sido truncado." if content_truncated else ""}
            
            Contenido:
            ```{file_type}
            {content_preview}
            ```
            
            Tipos de revisión solicitados: {', '.join(self.review_types)}
            Sugerir correcciones: {'Sí' if self.suggest_fixes else 'No'}
            
            Por favor, proporciona una revisión detallada en el siguiente formato JSON:
            
            ```json
            {{
                "issues": [
                    {{
                        "line": número_de_línea,
                        "severity": "critical|high|medium|low|info",
                        "type": "quality|security|performance",
                        "message": "Descripción del problema",
                        "suggestion": "Sugerencia de corrección (si aplica)"
                    }}
                ],
                "summary": "Resumen general de la revisión"
            }}
            
            Responde SOLO con el JSON, sin texto adicional.
            """
            
            # Obtener respuesta de la IA
            response = self.llm.invoke(prompt)
            
            # Intentar parsear la respuesta como JSON
            try:
                import json
                import re
                
                # Extraer JSON de la respuesta
                json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
                
                # Limpiar la cadena JSON
                json_str = re.sub(r'^```.*\n', '', json_str)
                json_str = re.sub(r'\n```$', '', json_str)
                
                result = json.loads(json_str)
                
                # Verificar y formatear el resultado
                if 'issues' not in result:
                    result['issues'] = []
                if 'summary' not in result:
                    result['summary'] = "No se encontraron problemas significativos."
                    
                # Añadir el archivo al resultado
                result['file'] = file_path
                
                return result
                
            except Exception as e:
                logger.error(f"Error al parsear la respuesta de la IA: {e}")
                logger.debug(f"Respuesta recibida: {response}")
                
                # Fallback: crear un resultado básico
                return {
                    'file': file_path,
                    'issues': [],
                    'summary': "Error al procesar la revisión con IA. Se recomienda revisar manualmente."
                }
                
        except Exception as e:
            logger.error(f"Error al revisar archivo con IA: {e}")
            # Fallback al método tradicional
            return self._review_file(file_path, content, event_type)
            
    def _get_file_type(self, file_ext):
        """
        Determina el tipo de archivo basado en su extensión.
        
        Args:
            file_ext (str): Extensión del archivo.
            
        Returns:
            str: Tipo de archivo para el highlighting.
        """
        file_types = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.sh': 'bash',
            '.bat': 'batch',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.md': 'markdown',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml'
        }
        
        return file_types.get(file_ext, 'text')
    
    def _check_code_quality(self, content, file_ext):
        """
        Revisa problemas de calidad de código.
        
        Args:
            content (str): Contenido del archivo.
            file_ext (str): Extensión del archivo.
            
        Returns:
            list: Lista de problemas de calidad encontrados.
        """
        issues = []
        
        # Verificar longitud de líneas (más de 100 caracteres)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if len(line) > 100:
                issues.append({
                    'type': 'quality',
                    'severity': 'low',
                    'line': i + 1,
                    'message': f'Línea demasiado larga ({len(line)} caracteres)',
                    'code': line[:50] + '...' if len(line) > 50 else line
                })
        
        # Verificar funciones muy largas (Python)
        if file_ext == '.py':
            function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(.*?\):'
            for match in re.finditer(function_pattern, content):
                func_name = match.group(1)
                func_start = content[:match.start()].count('\n') + 1
                
                # Contar líneas de la función
                func_content = content[match.start():]
                func_lines = 0
                indent = None
                
                for line in func_content.split('\n')[1:]:  # Saltar la línea de definición
                    if not line.strip():
                        continue
                        
                    # Determinar la indentación base
                    if indent is None:
                        match_indent = re.match(r'^(\s+)', line)
                        if match_indent:
                            indent = len(match_indent.group(1))
                        else:
                            break
                    
                    # Si encontramos una línea con menor indentación, hemos salido de la función
                    curr_indent = len(re.match(r'^(\s*)', line).group(1))
                    if curr_indent < indent:
                        break
                        
                    func_lines += 1
                
                if func_lines > 30:
                    issues.append({
                        'type': 'quality',
                        'severity': 'medium',
                        'line': func_start,
                        'message': f'Función {func_name} demasiado larga ({func_lines} líneas)',
                        'code': f'def {func_name}(...)'
                    })
        
        # Verificar nombres de variables muy cortos
        var_pattern = r'(?:^|\s+)([a-z][a-z0-9]?)\s*='
        for match in re.finditer(var_pattern, content, re.MULTILINE):
            var_name = match.group(1)
            if len(var_name) < 2 and var_name not in ['i', 'j', 'k', 'x', 'y', 'z']:
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'quality',
                    'severity': 'low',
                    'line': line_num,
                    'message': f'Nombre de variable demasiado corto: {var_name}',
                    'code': content.split('\n')[line_num - 1].strip()
                })
        
        return issues
    
    def _check_security_issues(self, content, file_ext):
        """
        Revisa problemas de seguridad en el código.
        
        Args:
            content (str): Contenido del archivo.
            file_ext (str): Extensión del archivo.
            
        Returns:
            list: Lista de problemas de seguridad encontrados.
        """
        issues = []
        
        # Verificar hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\']([^"\']+)["\']', 'Contraseña hardcoded'),
            (r'api[_-]?key\s*=\s*["\']([^"\']+)["\']', 'API Key hardcoded'),
            (r'secret\s*=\s*["\']([^"\']+)["\']', 'Secret hardcoded'),
            (r'token\s*=\s*["\']([^"\']+)["\']', 'Token hardcoded')
        ]
        
        for pattern, message in secret_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'security',
                    'severity': 'high',
                    'line': line_num,
                    'message': message,
                    'code': content.split('\n')[line_num - 1].strip()
                })
        
        # Verificar inyección SQL (Python)
        if file_ext == '.py':
            sql_patterns = [
                r'execute\s*\(\s*[f]?["\']SELECT.*?\{',
                r'execute\s*\(\s*[f]?["\']INSERT.*?\{',
                r'execute\s*\(\s*[f]?["\']UPDATE.*?\{',
                r'execute\s*\(\s*[f]?["\']DELETE.*?\{'
            ]
            
            for pattern in sql_patterns:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'line': line_num,
                        'message': 'Posible inyección SQL con f-string',
                        'code': content.split('\n')[line_num - 1].strip()
                    })
        
        # Verificar deserialización insegura (Python)
        if file_ext == '.py':
            unsafe_deserialize = [
                (r'pickle\.loads?\(', 'Uso inseguro de pickle'),
                (r'yaml\.load\((?!.*Loader=yaml\.SafeLoader)', 'Uso inseguro de yaml.load'),
                (r'eval\(', 'Uso de eval')
            ]
            
            for pattern, message in unsafe_deserialize:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'line': line_num,
                        'message': message,
                        'code': content.split('\n')[line_num - 1].strip()
                    })
        
        return issues
    
    def _check_performance_issues(self, content, file_ext):
        """
        Revisa problemas de rendimiento en el código.
        
        Args:
            content (str): Contenido del archivo.
            file_ext (str): Extensión del archivo.
            
        Returns:
            list: Lista de problemas de rendimiento encontrados.
        """
        issues = []
        
        # Verificar uso ineficiente de listas (Python)
        if file_ext == '.py':
            # Concatenación de strings en bucle
            string_concat = r'for\s+.*?:\s*.*?\s*\+='
            for match in re.finditer(string_concat, content):
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'line': line_num,
                    'message': 'Concatenación ineficiente de strings en bucle',
                    'code': content.split('\n')[line_num - 1].strip()
                })
            
            # Uso de + para concatenar listas
            list_concat = r'\[.*?\]\s*\+\s*\[.*?\]'
            for match in re.finditer(list_concat, content):
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'performance',
                    'severity': 'low',
                    'line': line_num,
                    'message': 'Uso de + para concatenar listas (usar extend)',
                    'code': content.split('\n')[line_num - 1].strip()
                })
            
            # Uso de list comprehension dentro de bucle
            list_in_loop = r'for\s+.*?:\s*.*?\[.*?for\s+.*?in'
            for match in re.finditer(list_in_loop, content):
                line_num = content[:match.start()].count('\n') + 1
                issues.append({
                    'type': 'performance',
                    'severity': 'medium',
                    'line': line_num,
                    'message': 'List comprehension dentro de bucle',
                    'code': content.split('\n')[line_num - 1].strip()
                })
        
        return issues
    
    def _generate_fix_suggestion(self, issue, content, file_ext):
        """
        Genera una sugerencia para corregir un problema.
        
        Args:
            issue (dict): Información sobre el problema.
            content (str): Contenido del archivo.
            file_ext (str): Extensión del archivo.
            
        Returns:
            str: Sugerencia para corregir el problema.
        """
        # En una implementación real, aquí se usaría IA para generar sugerencias específicas
        # Por ahora, generamos sugerencias genéricas basadas en el tipo de problema
        
        if issue['type'] == 'quality':
            if 'Línea demasiado larga' in issue['message']:
                return "Divide esta línea en múltiples líneas para mejorar la legibilidad."
                
            if 'Función demasiado larga' in issue['message']:
                return "Refactoriza esta función en múltiples funciones más pequeñas con responsabilidades específicas."
                
            if 'Nombre de variable demasiado corto' in issue['message']:
                return "Usa nombres de variables más descriptivos que expliquen su propósito."
        
        elif issue['type'] == 'security':
            if 'hardcoded' in issue['message']:
                return "Mueve este valor a una variable de entorno o archivo de configuración seguro."
                
            if 'inyección SQL' in issue['message']:
                return "Usa consultas parametrizadas o un ORM en lugar de construir consultas SQL con strings."
                
            if 'pickle' in issue['message']:
                return "Usa un formato de serialización más seguro como JSON."
                
            if 'yaml.load' in issue['message']:
                return "Usa yaml.safe_load() en lugar de yaml.load()."
                
            if 'eval' in issue['message']:
                return "Evita usar eval() y busca alternativas más seguras."
        
        elif issue['type'] == 'performance':
            if 'Concatenación ineficiente de strings' in issue['message']:
                return "Usa una lista para almacenar los strings y luego ''.join(lista) al final del bucle."
                
            if 'Uso de + para concatenar listas' in issue['message']:
                return "Usa lista1.extend(lista2) en lugar de lista1 + lista2."
                
            if 'List comprehension dentro de bucle' in issue['message']:
                return "Mueve la list comprehension fuera del bucle o usa un generador."
        
        return "Revisa este problema y considera refactorizar el código."
    
    @classmethod
    def get_config_schema(cls):
        """
        Devuelve el esquema de configuración para este módulo.
        
        Returns:
            dict: Esquema de configuración.
        """
        return {
            'review_types': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': ['quality', 'security', 'performance'],
                'description': 'Tipos de revisión a realizar'
            },
            'suggest_fixes': {
                'type': 'boolean',
                'default': True,
                'description': 'Generar sugerencias para corregir problemas'
            },
            'severity_threshold': {
                'type': 'string',
                'enum': ['high', 'medium', 'low'],
                'default': 'low',
                'description': 'Umbral de severidad para reportar problemas'
            },
            'enabled': {
                'type': 'boolean',
                'default': True,
                'description': 'Activar/desactivar este módulo'
            },
            'use_ai': {
                'type': 'boolean',
                'default': False,
                'description': 'Usar inteligencia artificial para generar sugerencias'
            }
        }
