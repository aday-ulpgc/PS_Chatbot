#!/usr/bin/env python3
"""Script de prueba para verificar funcionalidad de DELETE y GET citas eliminadas."""

import requests
import json
from datetime import datetime, timedelta

# URL base de la API
BASE_URL = "http://localhost:8000"

print("=" * 80)
print("PRUEBA DE FUNCIONALIDAD: DELETE y GET CITAS ELIMINADAS")
print("=" * 80)

# ── PASO 1: Crear un usuario de prueba ──────────────────────────────────────
print("\n📝 PASO 1: Crear usuario de prueba...")
usuario_data = {
    "TIPO": "I",
    "NOMBRE": "Usuario Prueba API",
    "EMAIL": f"prueba_api_{datetime.now().timestamp()}@test.com",
    "CONTRASENA": "password123"
}

response = requests.post(f"{BASE_URL}/usuarios", json=usuario_data)
if response.status_code == 201:
    usuario = response.json()
    id_usuario = usuario["ID_USUARIO"]
    print(f"✅ Usuario creado (ID: {id_usuario})")
else:
    print(f"❌ Error al crear usuario: {response.text}")
    exit(1)

# ── PASO 2: Crear un contacto ──────────────────────────────────────────────
print("\n📝 PASO 2: Crear contacto...")
contacto_data = {
    "NOMBRE": "Dr. Test",
    "EMAIL": "dr.test@clinic.com"
}

response = requests.post(f"{BASE_URL}/usuarios/{id_usuario}/contactos", json=contacto_data)
if response.status_code == 201:
    contacto = response.json()
    id_contacto = contacto["ID_CONTACTO"]
    print(f"✅ Contacto creado (ID: {id_contacto})")
else:
    print(f"❌ Error al crear contacto: {response.text}")
    exit(1)

# ── PASO 3: Crear una cita ─────────────────────────────────────────────────
print("\n📝 PASO 3: Crear cita...")
fecha_cita = datetime.now() + timedelta(days=10)
cita_data = {
    "ID_USUARIO": id_usuario,
    "ID_CONTACTO": id_contacto,
    "FECHA": fecha_cita.isoformat(),
    "DESCRIPCION": "Cita de prueba para DELETE",
    "PRIORIDAD": 1
}

response = requests.post(f"{BASE_URL}/citas", json=cita_data)
if response.status_code == 201:
    cita = response.json()
    id_cita = cita["ID_CITA"]
    print(f"✅ Cita creada (ID: {id_cita})")
    print(f"   - Descripción: {cita['DESCRIPCION']}")
    print(f"   - Fecha: {cita['FECHA']}")
    print(f"   - ELIMINADO: {cita['ELIMINADO']}")
else:
    print(f"❌ Error al crear cita: {response.text}")
    exit(1)

# ── PASO 4: Verificar que la cita está ACTIVA (ELIMINADO = null) ────────────
print("\n📝 PASO 4: Obtener citas ACTIVAS del usuario...")
response = requests.get(f"{BASE_URL}/usuarios/{id_usuario}/citas")
if response.status_code == 200:
    citas_activas = response.json()
    print(f"✅ Citas activas obtenidas: {len(citas_activas)}")
    for c in citas_activas:
        if c["ID_CITA"] == id_cita:
            print(f"   ✅ Encontrada nuestra cita (ID: {id_cita})")
            print(f"   - ELIMINADO: {c['ELIMINADO']} (NULL = activa)")
else:
    print(f"❌ Error al obtener citas: {response.text}")

# ── PASO 5: ELIMINAR la cita (Soft Delete) ────────────────────────────────
print("\n🗑️  PASO 5: ELIMINAR la cita (Soft Delete)...")
response = requests.delete(f"{BASE_URL}/citas/{id_cita}")
if response.status_code == 204:
    print(f"✅ Cita eliminada (status 204 No Content)")
else:
    print(f"❌ Error al eliminar cita: {response.status_code}")

# ── PASO 6: Verificar que la cita NO está en activas ──────────────────────
print("\n📝 PASO 6: Obtener citas ACTIVAS después de deletear...")
response = requests.get(f"{BASE_URL}/usuarios/{id_usuario}/citas")
if response.status_code == 200:
    citas_activas = response.json()
    print(f"✅ Citas activas obtenidas: {len(citas_activas)}")
    cita_encontrada = any(c["ID_CITA"] == id_cita for c in citas_activas)
    if cita_encontrada:
        print(f"❌ ERROR: La cita eliminada sigue en activas!")
    else:
        print(f"✅ CORRECTO: La cita NO aparece en citas activas")
else:
    print(f"❌ Error al obtener citas: {response.text}")

# ── PASO 7: Obtener citas ELIMINADAS ───────────────────────────────────────
print("\n📝 PASO 7: Obtener citas ELIMINADAS del usuario...")
response = requests.get(f"{BASE_URL}/usuarios/{id_usuario}/citas/eliminadas")
if response.status_code == 200:
    citas_eliminadas = response.json()
    print(f"✅ Citas eliminadas obtenidas: {len(citas_eliminadas)}")
    
    cita_encontrada = None
    for c in citas_eliminadas:
        if c["ID_CITA"] == id_cita:
            cita_encontrada = c
            break
    
    if cita_encontrada:
        print(f"✅ CORRECTO: Cita eliminada encontrada!")
        print(f"   - ID_CITA: {cita_encontrada['ID_CITA']}")
        print(f"   - Descripción: {cita_encontrada['DESCRIPCION']}")
        print(f"   - ELIMINADO: {cita_encontrada['ELIMINADO']} (tiene fecha = eliminada)")
    else:
        print(f"❌ ERROR: La cita eliminada NO aparece en citas eliminadas!")
else:
    print(f"❌ Error al obtener citas eliminadas: {response.text}")

print("\n" + "=" * 80)
print("✅ PRUEBA COMPLETADA")
print("=" * 80)

# ── Mostrar queries de verificación en DBeaver ─────────────────────────────
print("\n📊 QUERIES PARA VERIFICAR EN DBEAVER:")
print("\n1️⃣  Ver la cita deleted (ELIMINADO tiene fecha):")
print(f"   SELECT ID_CITA, DESCRIPCION, ELIMINADO FROM CITAS_IND WHERE ID_CITA = {id_cita};")
print("\n2️⃣  Ver todas las citas del usuario (incluyendo eliminadas):")
print(f"   SELECT ID_CITA, DESCRIPCION, ELIMINADO FROM CITAS_IND WHERE ID_USUARIO = {id_usuario};")
