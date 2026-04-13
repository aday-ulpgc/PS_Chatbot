import requests

class WhatsAppClient:
    """Cliente para enviar mensajes a través de la API de WhatsApp Business."""
    
    def __init__(self, token: str, phone_id: str):
        self.token = token
        self.phone_id = phone_id
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_id}/messages"

    def enviar_texto(self, numero_destino: str, texto: str) -> bool:
        """Envía un mensaje de texto simple a un usuario."""
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": numero_destino,
            "type": "text",
            "text": {"body": texto}
        }
        
        respuesta = requests.post(self.base_url, headers=headers, json=payload)
        
        if respuesta.status_code == 200:
            print(f"✅ [API] Mensaje enviado correctamente a {numero_destino}")
            return True
        else:
            print(f"❌ [API] Error al enviar: {respuesta.text}")
            return False