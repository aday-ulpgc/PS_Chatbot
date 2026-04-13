from fastapi import FastAPI, Request
import uvicorn
from bot.whatsapp.client import WhatsAppClient

app = FastAPI(title="SaaS-Bot WhatsApp")

# --- CREDENCIALES ---
VERIFY_TOKEN = "patata123"
META_TOKEN = "EAAVFDHsPbhYBRAtctSpdZBBq0vDw2xoa2wYuZAfZAyVZBvyK5O6v1gfXT99MRUSSdZCtK0gDHpR6cXyuz9fpyPDr8whXVRu2rPU1GP5LZAlczZBriZBDROZCFQKCtMQJ5Txr3BMYzlh6KKX0PxSksN7vwuwwzXPtZA1ZCWp8X7vSja4oYaxgsH3R93hMTnZBdLmkNLlhxZCMisAkSvbK6vZAAB73m2qidd62Wa0ZBCT6QtU3uRT8Xs3zXeGNEgTb4chS0ZCOicPIpXzb12h7UJVfz8LxZCkQ4"  # ¡Pon tu token real!
ID_TELEFONO = "1024526427418217" 

cliente_wa = WhatsAppClient(token=META_TOKEN, phone_id=ID_TELEFONO)

@app.get("/")
def home():
    return {"status": "Servidor Activo 🟢"}

@app.get("/webhook")
async def verificar_webhook(request: Request):
    """Ruta para que Meta verifique la conexión."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return "Error de verificación", 403

@app.post("/webhook")
async def recibir_mensaje(request: Request):
    """Ruta que recibe los mensajes entrantes de los clientes."""
    body = await request.json()
    
    try:
        cambios = body["entry"][0]["changes"][0]["value"]
        if "messages" in cambios:
            mensaje = cambios["messages"][0]
            numero_cliente = mensaje["from"]
            texto = mensaje["text"]["body"]
            
            print(f"📩 [Usuario {numero_cliente}]: {texto}")
            
            cliente_wa.enviar_texto(
                numero_destino=numero_cliente, 
                texto=f"Diablo. Has dicho: '{texto}'"
            )
            
    except Exception as e:
        pass # Ignorar eventos que no son mensajes de texto
        
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main_whatsapp:app", host="0.0.0.0", port=8000, reload=True)