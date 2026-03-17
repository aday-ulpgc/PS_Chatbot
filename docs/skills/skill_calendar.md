# SKILL: Google Calendar API & OAuth2
**Descripción:** Cómo autenticar e interactuar con Google Calendar a coste 0€.
## Reglas de Implementación
1. **Librerías:** Usa `google-api-python-client`, `google-auth-httplib2` y `google-auth-oauthlib`.
2. **Arquitectura:** Toda la lógica de conexión debe vivir en `src/services/calendar_service.py`.
3. **Flujo de Autenticación (OAuth2):**
   - El código debe buscar un archivo local llamado `credentials.json`.
   - Usa `InstalledAppFlow.from_client_secrets_file` para generar el login web la primera vez.
   - El token de sesión resultante DEBE guardarse en un archivo local llamado `token.json`.
4. **Scopes:** Solicita solo los permisos estrictamente necesarios: `['https://www.googleapis.com/auth/calendar.readonly']`.
5. **Manejo de Errores:** Captura excepciones de red y credenciales inválidas, devolviendo mensajes limpios.
