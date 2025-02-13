# Git Monitor

Monitor de cambios en repositorios Git con análisis de AI y notificaciones a Slack.

## Características

- 🔍 Monitoreo en tiempo real de cambios en repositorios Git
- 🤖 Análisis de cambios usando GPT-3.5
- 💬 Notificaciones a Slack
- 📝 Detección de cambios locales y commits
- 📊 Análisis detallado de modificaciones

## Configuración

1. Crea un archivo `.env` con las siguientes variables:
```env
OPENAI_API_KEY=tu_api_key
SLACK_BOT_TOKEN=xoxb-tu-token
SLACK_CHANNEL_ID=tu-channel-id
REPO_PATH=ruta/a/tu/repo
REPO_BRANCH=main
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecuta el monitor:
```bash
python main.py
```

## Uso

El monitor detectará automáticamente:
- Nuevos commits en el repositorio
- Cambios locales en archivos
- Modificaciones pendientes de commit

Cada cambio será analizado y enviado a Slack con un resumen detallado.
