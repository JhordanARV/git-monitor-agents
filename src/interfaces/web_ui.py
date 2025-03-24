import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from src.core.module_registry import ModuleRegistry
from src.core.config_manager import ConfigManager
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates'),
           static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static'))

config_manager = None

def init_app(config_path=None):
    """
    Inicializa la aplicación Flask.
    
    Args:
        config_path (str, opcional): Ruta al archivo de configuración.
    """
    global config_manager
    config_manager = ConfigManager(config_path)
    logger.info("Aplicación web inicializada")
    return app

@app.route('/')
def index():
    """Página principal de configuración."""
    modules = ModuleRegistry.get_all_modules()
    module_configs = {name: cls.get_config_schema() for name, cls in modules.items()}
    current_config = config_manager.get_config()
    
    return render_template('config.html', 
                          modules=modules,
                          module_configs=module_configs,
                          current_config=current_config)

@app.route('/api/config', methods=['GET', 'POST'])
def config_api():
    """API para obtener/actualizar la configuración."""
    if request.method == 'GET':
        return jsonify(config_manager.get_config())
    
    # POST - actualizar configuración
    new_config = request.json
    success = config_manager.update_config(new_config)
    return jsonify({'status': 'success' if success else 'error'})

@app.route('/api/modules', methods=['GET'])
def modules_api():
    """API para obtener información de los módulos."""
    modules = ModuleRegistry.get_all_modules()
    result = {}
    
    for name, cls in modules.items():
        result[name] = {
            'description': cls.__doc__,
            'config_schema': cls.get_config_schema()
        }
    
    return jsonify(result)

@app.route('/module/<module_name>', methods=['GET', 'POST'])
def module_config(module_name):
    """Página de configuración para un módulo específico."""
    module_class = ModuleRegistry.get_module(module_name)
    
    if not module_class:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Actualizar configuración del módulo
        module_config = {}
        schema = module_class.get_config_schema()
        
        for key, schema_item in schema.items():
            if schema_item['type'] == 'boolean':
                module_config[key] = key in request.form
            elif schema_item['type'] == 'array':
                values = request.form.getlist(key)
                module_config[key] = values
            else:
                module_config[key] = request.form.get(key, schema_item.get('default', ''))
        
        # Actualizar configuración
        current_config = config_manager.get_config()
        if 'modules' not in current_config:
            current_config['modules'] = {}
        current_config['modules'][module_name] = module_config
        config_manager.update_config(current_config)
        
        return redirect(url_for('index'))
    
    # GET - mostrar formulario de configuración
    module_config = config_manager.get_module_config(module_name)
    schema = module_class.get_config_schema()
    
    return render_template('module_config.html',
                          module_name=module_name,
                          module_description=module_class.__doc__,
                          schema=schema,
                          config=module_config)

@app.route('/commit-messages', methods=['GET'])
def commit_messages():
    """Página para generar y mostrar mensajes de commit."""
    # Obtener los últimos mensajes generados (si existen)
    return render_template('commit_messages.html')

@app.route('/api/generate-commit-message', methods=['POST'])
def generate_commit_message():
    """API para generar un mensaje de commit manualmente."""
    try:
        # Obtener datos del formulario
        source_type = request.form.get('source_type', 'file')
        file_path = request.form.get('file_path', '')
        event_type = request.form.get('event_type', 'modified')
        
        # Obtener la ruta del repositorio desde la configuración
        repo_path = config_manager.get_config().get('core', {}).get('repo_path', '.')
        
        # Obtener instancia del generador de mensajes
        commit_generator_class = ModuleRegistry.get_module('CommitMessageGenerator')
        
        if not commit_generator_class:
            return jsonify({'error': 'Módulo CommitMessageGenerator no encontrado'}), 404
            
        # Crear instancia con la configuración
        module_config = config_manager.get_module_config('CommitMessageGenerator')
        commit_generator = commit_generator_class(module_config)
        
        # Generar mensaje según el tipo de origen
        if source_type == 'file':
            if not file_path:
                return jsonify({'error': 'Se requiere la ruta del archivo'}), 400
                
            # Crear evento simulado para un archivo específico
            event_data = {
                'path': file_path,
                'event_type': event_type,
                'content': '',  # No tenemos contenido real aquí
                'repo_path': repo_path
            }
            
            # Generar mensaje para un archivo específico
            result = commit_generator.process(event_data)
            
        else:  # source_type == 'staged'
            # Generar mensaje para cambios en stage
            result = commit_generator.process_staged_changes(repo_path)
        
        if not result or not result.get('success'):
            return jsonify({'error': 'Error al generar mensaje de commit'}), 500
            
        return jsonify({
            'message': result.get('commit_message', ''),
            'summary': result.get('summary', '')
        })
        
    except Exception as e:
        logger.exception(f"Error al generar mensaje de commit: {e}")
        return jsonify({'error': str(e)}), 500

def start_server(host='0.0.0.0', port=5000, debug=False):
    """
    Inicia el servidor web.
    
    Args:
        host (str, opcional): Host para escuchar. Por defecto es '0.0.0.0'.
        port (int, opcional): Puerto para escuchar. Por defecto es 5000.
        debug (bool, opcional): Modo debug. Por defecto es False.
    """
    app.run(host=host, port=port, debug=debug)
