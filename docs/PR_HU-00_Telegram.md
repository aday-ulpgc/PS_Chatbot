# Reporte de Entrega: HU-00 - Interfaz Base del Bot de Telegram

**Rol:** El Narrador
**Objetivo:** Establecer la base técnica y la conexión inicial del bot de Telegram.

## 1. Resumen Funcional
El bot ha sido inicializado exitosamente y ya es capaz de conectarse a los servidores de Telegram. Actualmente, si un usuario envía el comando `/start`, el bot responde automáticamente con el mensaje: *"¡Hola! Soy tu bot de gestión de citas"*. Esta es la prueba de vida de que la comunicación bidireccional funciona correctamente.

## 2. Arquitectura Técnica
Para esta primera iteración, hemos implementado una arquitectura modular y segura:
- **`python-dotenv`**: Integramos esta librería para cargar automáticamente las credenciales desde el archivo local `env/.env`. Esto garantiza que los tokens sensibles nunca se suban al repositorio (cumpliendo estrictamente con nuestras directrices de seguridad).
- **`ApplicationBuilder`**: Utilizamos el patrón oficial de inicialización de `python-telegram-bot` (v21+) dentro de `src/main.py`. Este módulo actúa como orquestador: valida el entorno, construye la aplicación, inyecta el token y arranca el ciclo de escucha de eventos (polling).
- **Handlers "Tontos"**: La respuesta estática al comando vive separada en `src/bot/telegram_handler.py`. Esto mantiene a `main.py` limpio y establece el patrón correcto: el handler recibe el mensaje, y (en futuras HU) delegará el trabajo complejo a `src/services/`.

## 3. Parche de Estabilidad: Asyncio en Windows
Durante la integración, nos anticipamos a un error común al ejecutar aplicaciones asíncronas en Windows con Python 3.8+ (muy presente en 3.12+). Python en Windows usa por defecto el `ProactorEventLoop`, el cual suele causar inestabilidad, errores de "Event loop is closed", y cierres abruptos al interactuar con ciertas funciones de red de `python-telegram-bot`.

Para evitar que el entorno de desarrollo local nos falle, hemos introducido este parche en `main.py`:
```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```
Esto fuerza al sistema a usar el `SelectorEventLoop` clásico y más estable en Windows. Adicionalmente, añadimos un bloque `try-except` para garantizar que el loop de eventos esté siempre inicializado antes de que el bot lo requiera, evitando errores de inicialización en tiempo de ejecución.

## 4. Guía de Pruebas para el Equipo
Para probar que el bot funciona en tu entorno local, sigue estos pasos exactos:

1. **Instala las dependencias actualizadas** (se ha añadido `python-dotenv`):
   ```bash
   pip install -r requirements.txt
   ```

2. **Configura tus credenciales**:
   - Navega hasta la carpeta `env/`.
   - Crea un archivo llamado **exactamente** `.env` (si no lo tienes ya).
   - Edita el archivo y añade tu token de bot (sin comillas):
     ```env
     TELEGRAM_TOKEN=tu_token_aqui_proporcionado_por_botfather
     ```

3. **Ejecuta el bot**:
   Abre una terminal en la raíz del proyecto (`Proyecto Bot/`) y ejecuta el orquestador:
   ```bash
   python src/main.py
   ```
   Deberías ver el mensaje: *Bot iniciado. Esperando mensajes...*

4. **Verifica la funcionalidad**:
   - Abre Telegram en tu móvil o PC.
   - Entra en el chat del bot.
   - Escribe y envía el comando `/start`.
   - El bot debe contestarte inmediatamente.
