import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
import uvicorn
from bot.whatsapp.client import WhatsAppClient

app = FastAPI(title="SaaS-Bot WhatsApp")


dotenv_path: str = os.path.join(os.path.dirname(__file__), "..", "env", ".env")
load_dotenv(dotenv_path=dotenv_path)

meta_token: str | None = os.getenv("META_TOKEN")
phone_id: str | None = os.getenv("ID_TELEFONO")
verify_token: str | None = os.getenv("VERIFY_TOKEN")
cliente_wa = WhatsAppClient(token=meta_token, phone_id=phone_id)

@app.get("/")
def home():
    return {"status": "Servidor Activo 🟢"}

@app.get("/webhook")
async def verificar_webhook(request: Request):
    """Ruta para que Meta verifique la conexión."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
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