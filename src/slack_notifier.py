from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging

logger = logging.getLogger(__name__)

class SlackNotifier:
    def __init__(self, token: str, channel: str):
        if not token:
            logger.error("Token de Slack no proporcionado")
            raise ValueError("Se requiere un token de Slack")
        if not channel:
            logger.error("ID del canal de Slack no proporcionado")
            raise ValueError("Se requiere un ID de canal de Slack")
            
        logger.info(f"Inicializando SlackNotifier para el canal: {channel}")
        self.client = WebClient(token=token)
        self.channel = channel

    def send_message(self, message: str) -> bool:
        """
        Send a message to the configured Slack channel
        Returns True if successful, False otherwise
        """
        try:
            logger.info(f"Intentando enviar mensaje a Slack al canal {self.channel}")
            logger.debug(f"Contenido del mensaje: {message[:100]}...")  # Solo los primeros 100 caracteres
            
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message,
                unfurl_links=True,
                unfurl_media=True
            )
            
            if response["ok"]:
                logger.info("Mensaje enviado exitosamente a Slack")
            else:
                logger.error(f"Error al enviar mensaje a Slack: {response.get('error', 'Unknown error')}")
                logger.debug(f"Respuesta completa de Slack: {response}")
            return response["ok"]
            
        except SlackApiError as e:
            error_response = e.response.get('error', 'Unknown error')
            error_detail = getattr(e, 'response', {}).get('detail', 'No detail available')
            logger.error(f"Error enviando mensaje a Slack: {error_response}")
            logger.error(f"Detalles del error: {error_detail}")
            logger.error(f"Response completa: {e.response}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado al enviar mensaje a Slack: {str(e)}")
            return False
