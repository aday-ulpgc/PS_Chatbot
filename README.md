[![CI/CD Pipeline](https://github.com/aday-ulpgc/PS_Chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/aday-ulpgc/PS_Chatbot/actions)

# SaaS-Bot NLP (Gestión Inteligente de Citas)

Bienvenido al repositorio oficial del **Grupo 06** para la asignatura de Producción de Software (Curso 2025/2026).

## Arquitectura del Proyecto
Aplicamos **Spec-Driven Development (SDD)**. La arquitectura es modular y separa la interfaz gráfica de la lógica de negocio:
- `src/bot/`: Contiene exclusivamente los handlers e interfaz de Telegram.
- `src/services/`: Contiene la lógica de negocio (Google Calendar API) y el motor NLP (`src/nlp/`).

## Setup Local

Sigue estos pasos para levantar el entorno en tu máquina local:

1. Clona el repositorio:
   ```bash
   git clone <url-del-repositorio>
   cd "Proyecto Bot"
   ```
2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   ```
3. Activa el entorno virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

> ⚠️ **Atención:** Nunca subáis los archivos `.env`, `credentials.json` o `token.json` al repositorio. Están protegidos por el `.gitignore`.
