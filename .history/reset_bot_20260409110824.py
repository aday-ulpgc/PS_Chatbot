"""Script para limpiar la sesión anterior del bot en Telegram"""

import os
import sys
import requests
from dotenv import load_dotenv

dotenv_path: str = os.path.join(os.path.dirname(__file__), "..", "env", ".env")
load_dotenv(dotenv_path=dotenv_path)

token: str | None = os.getenv("TELEGRAM_TOKEN")

if not token:
    print("ERROR: TELEGRAM_TOKEN no encontrado en .env")
    sys.exit(1)

# Resetear el dropPendingUpdates de Telegram
url = f"https://api.telegram.org/bot{token}/deleteWebhook"
params = {"drop_pending_updates": True}

print("Limpiando sesiones anteriores del bot...")
response = requests.post(url, params=params)

if response.status_code == 200:
    print("✅ Sesión limpiada correctamente")
else:
    print(f"⚠️ Error al limpiar: {response.status_code}")

print("\nAhora arranca el bot con: python src/main.py")
