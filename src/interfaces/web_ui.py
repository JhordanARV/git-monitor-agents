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

def start_server(host='0.0.0.0', port=5000, debug=False):
    """
    Inicia el servidor web.
    
    Args:
        host (str, opcional): Host para escuchar. Por defecto es '0.0.0.0'.
        port (int, opcional): Puerto para escuchar. Por defecto es 5000.
        debug (bool, opcional): Modo debug. Por defecto es False.
    """
    app.run(host=host, port=port, debug=debug)
