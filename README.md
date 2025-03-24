# Git Monitor

Monitor de cambios en repositorios Git con análisis de AI y notificaciones a Slack.

## Características

- 🔍 Monitoreo en tiempo real de cambios en repositorios Git
- 🤖 Análisis de cambios usando módulos especializados
- 💬 Notificaciones a Slack
- 📝 Detección de cambios locales y commits
- 📊 Análisis detallado de modificaciones
- 🧩 Arquitectura modular extensible
- 🌐 Interfaz web para configuración

## Nueva Arquitectura Modular

La nueva versión de Git Monitor implementa una arquitectura modular que permite:

- ✅ Añadir nuevos módulos de análisis fácilmente
- ✅ Configurar cada módulo de forma independiente
- ✅ Activar o desactivar módulos según necesidades
- ✅ Interfaz web para gestión de configuración

## Tecnologías Utilizadas

El proyecto Git Monitor utiliza las siguientes tecnologías:

### Backend
- **Python**: Lenguaje principal de desarrollo
- **GitPython**: Para interactuar con repositorios Git
- **Flask**: Para la interfaz web de configuración
- **PyYAML**: Para la gestión de configuración
- **Watchdog**: Para monitoreo de cambios en archivos en tiempo real

### Inteligencia Artificial
- **OpenAI API**: Para análisis de código y generación de contenido
- **LangChain**: Framework para aplicaciones basadas en LLMs

### Comunicación
- **Slack SDK**: Para enviar notificaciones a canales de Slack

### Arquitectura
- **Patrón Modular**: Arquitectura extensible basada en módulos independientes
- **Patrón Observador**: Para monitoreo de eventos en tiempo real
- **Patrón Registro (Registry)**: Para gestión dinámica de módulos

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/tu-usuario/git-monitor.git
cd git-monitor
```

2. Crea un entorno virtual:
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Instala las dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

### Archivo .env

Crea un archivo `.env` con las siguientes variables:
```env
OPENAI_API_KEY=tu_api_key
SLACK_BOT_TOKEN=xoxb-tu-token
SLACK_CHANNEL_ID=tu-channel-id
REPO_PATH=ruta/a/tu/repo
REPO_BRANCH=master
```

### Archivo config.yaml

El sistema utiliza un archivo `config.yaml` para la configuración general y de módulos. Puedes modificarlo manualmente o a través de la interfaz web:

```yaml
core:
  repo_path: "."
  branch: "master"
  poll_interval: 300
  ai_provider: "openai"

modules:
  DocstringGenerator:
    format: "google"
    languages:
      - "python"
      - "javascript"
    enabled: true
  
  ImpactAnalyzer:
    risk_threshold: "medium"
    analyze_dependencies: true
    suggest_tests: true
    enabled: true
  
  CodeReviewer:
    review_types:
      - "quality"
      - "security"
      - "performance"
    suggest_fixes: true
    severity_threshold: "low"
    enabled: true
```

## Ejecución

### Modo Básico

Para ejecutar Git Monitor sin interfaz web:

```bash
python main.py
```

### Con Interfaz Web

Para ejecutar con la interfaz web de configuración:

```bash
python main.py --web --web-port=5000
```

Luego abre tu navegador en `http://localhost:5000`

### Opciones de Línea de Comandos

- `--config`: Ruta al archivo de configuración (por defecto: `config.yaml`)
- `--web`: Activa la interfaz web
- `--web-port`: Puerto para la interfaz web (por defecto: 5000)

Ejemplo:
```bash
python main.py --config=mi_config.yaml --web --web-port=8080
```

## Módulos Disponibles

### 1. Generador de Docstrings (DocstringGenerator)

Genera y actualiza automáticamente la documentación en el código.

**Configuración:**
- `format`: Formato de docstrings (google, numpy, sphinx)
- `languages`: Lenguajes a procesar
- `enabled`: Activar/desactivar el módulo

### 2. Analizador de Impacto (ImpactAnalyzer)

Analiza el impacto potencial de los cambios en el código y sugiere pruebas relevantes.

**Configuración:**
- `risk_threshold`: Umbral de riesgo (low, medium, high)
- `analyze_dependencies`: Analizar dependencias
- `suggest_tests`: Sugerir pruebas
- `enabled`: Activar/desactivar el módulo

### 3. Revisor de Código (CodeReviewer)

Revisa automáticamente el código y proporciona sugerencias de mejora.

**Configuración:**
- `review_types`: Tipos de revisión (quality, security, performance)
- `suggest_fixes`: Sugerir correcciones
- `severity_threshold`: Umbral de severidad
- `enabled`: Activar/desactivar el módulo

## Interfaz Web

La interfaz web permite:

1. Ver la configuración actual
2. Modificar la configuración general
3. Configurar cada módulo individualmente
4. Activar/desactivar módulos

## Extensibilidad

Para crear un nuevo módulo:

1. Crea una nueva carpeta en `src/modules/tu_modulo`
2. Implementa una clase que extienda `BaseModule`
3. Registra el módulo en `ModuleRegistry`

El sistema detectará automáticamente el nuevo módulo y lo incluirá en la configuración.
