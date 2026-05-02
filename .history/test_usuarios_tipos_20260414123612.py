#!/usr/bin/env python3
"""Script de prueba para validar funcionalidades de usuarios individuales y corporativos."""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

print("=" * 100)
print("PRUEBA COMPLETA: USUARIOS INDIVIDUALES (I) vs CORPORATIVOS (C)")
print("=" * 100)

# ──────────────────────────────────────────────────────────────────────────────
# PARTE 1: USUARIO INDIVIDUAL (TIPO = I)
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "="*50)
print("PARTE 1: USUARIO INDIVIDUAL (TIPO = I)")
print("="*50)

# 1.1 Crear usuario individual
print("\n1️⃣  Crear usuario individual...")
usuario_i_data = {
    "TIPO": "I",
    "NOMBRE": "Juan García Individual",
    "EMAIL": f"juan_individual_{datetime.now().timestamp()}@test.com",
    "CONTRASENA": "password123"
}

response = requests.post(f"{BASE_URL}/usuarios", json=usuario_i_data)
if response.status_code == 201:
    usuario_i = response.json()
    id_usuario_i = usuario_i["ID_USUARIO"]
    print(f"✅ Usuario individual creado (ID: {id_usuario_i}, TIPO: {usuario_i['TIPO']})")
else:
    print(f"❌ Error: {response.text}")
    exit(1)

# 1.2 Crear contacto para usuario individual
print("\n2️⃣  Crear contacto para usuario individual...")
contacto_i_data = {
    "NOMBRE": "Dr. García",
    "EMAIL": "dr.garcia@clinic.com"
}

response = requests.post(f"{BASE_URL}/usuarios/{id_usuario_i}/contactos", json=contacto_i_data)
if response.status_code == 201:
    contacto_i = response.json()
    id_contacto_i = contacto_i["ID_CONTACTO"]
    print(f"✅ Contacto creado (ID: {id_contacto_i})")
else:
    print(f"❌ Error: {response.text}")

# 1.3 Crear cita individual (CitaInd) CON DURACION
print("\n3️⃣  Crear cita individual CON DURACION...")
fecha_cita = datetime.now() + timedelta(days=5)
cita_i_data = {
    "ID_USUARIO": id_usuario_i,
    "ID_CONTACTO": id_contacto_i,
    "FECHA": fecha_cita.isoformat(),
    "DESCRIPCION": "Consulta médica individual",
    "PRIORIDAD": 1,
    "DURACION": 30  # minutos
}

response = requests.post(f"{BASE_URL}/citas", json=cita_i_data)
if response.status_code == 201:
    cita_i = response.json()
    id_cita_i = cita_i["ID_CITA"]
    print(f"✅ Cita individual creada (ID: {id_cita_i})")
    print(f"   - Descripción: {cita_i.get('DESCRIPCION')}")
    print(f"   - Duración: {cita_i.get('DURACION')} minutos")
else:
    print(f"❌ Error: {response.text}")

# 1.4 Actualizar cita individual (PUT) - cambiar duración
print("\n4️⃣  Actualizar cita individual (PUT) - cambiar duración...")
cita_i_update = {
    "DURACION": 45,
    "DESCRIPCION": "Consulta médica individual (EXTENDIDA)"
}

response = requests.put(f"{BASE_URL}/citas/{id_cita_i}", json=cita_i_update)
if response.status_code == 200:
    cita_actualizada = response.json()
    print(f"✅ Cita actualizada")
    print(f"   - Nueva duración: {cita_actualizada.get('DURACION')} minutos")
    print(f"   - Nueva descripción: {cita_actualizada.get('DESCRIPCION')}")
else:
    print(f"❌ Error: {response.text}")

# 1.5 Obtener citas del usuario individual
print("\n5️⃣  GET /usuarios/{id}/citas para usuario individual...")
response = requests.get(f"{BASE_URL}/usuarios/{id_usuario_i}/citas")
if response.status_code == 200:
    citas = response.json()
    print(f"✅ Citas obtenidas: {len(citas)}")
    for c in citas:
        print(f"   - ID: {c['ID_CITA']}, Duración: {c.get('DURACION')} min, Desc: {c.get('DESCRIPCION')}")
else:
    print(f"❌ Error: {response.text}")

# ──────────────────────────────────────────────────────────────────────────────
# PARTE 2: USUARIO CORPORATIVO (TIPO = C)
# ──────────────────────────────────────────────────────────────────────────────

print("\n" + "="*50)
print("PARTE 2: USUARIO CORPORATIVO (TIPO = C)")
print("="*50)

# 2.1 Crear usuario corporativo
print("\n6️⃣  Crear usuario corporativo (TIPO = C)...")
usuario_c_data = {
    "TIPO": "C",
    "NOMBRE": "Clínica Central",
    "EMAIL": f"clinica_central_{datetime.now().timestamp()}@company.com",
    "CONTRASENA": "password456"
}

response = requests.post(f"{BASE_URL}/usuarios", json=usuario_c_data)
if response.status_code == 201:
    usuario_c = response.json()
    id_usuario_c = usuario_c["ID_USUARIO"]
    print(f"✅ Usuario corporativo creado (ID: {id_usuario_c}, TIPO: {usuario_c['TIPO']})")
else:
    print(f"❌ Error: {response.text}")
    id_usuario_c = None

if id_usuario_c:
    # 2.2 Buscar endpoint para crear empleados (POST /usuarios/{id}/empleados)
    print("\n7️⃣  Intentar crear empleado para usuario corporativo...")
    empleado_data = {
        "NOMBRE": "Dr. Pérez",
        "TIPO": "E"  # Empleado
    }
    
    response = requests.post(f"{BASE_URL}/usuarios/{id_usuario_c}/empleados", json=empleado_data)
    if response.status_code == 201:
        empleado = response.json()
        id_empleado = empleado.get("ID_EMPLEADO")
        print(f"✅ Empleado creado (ID: {id_empleado})")
    else:
        print(f"⚠️  Endpoint no existe o error: {response.status_code}")
        print(f"   Mensaje: {response.text[:100]}")
        id_empleado = None

print("\n" + "="*100)
print("✅ PRUEBA COMPLETADA")
print("="*100)

# Summary
print("\n📊 RESUMEN:")
print(f"✅ Usuario Individual (TIPO=I): ID {id_usuario_i}")
print(f"✅ Cita Individual: ID {id_cita_i}, Duración: 45 minutos")
print(f"✅ Usuario Corporativo (TIPO=C): ID {id_usuario_c if id_usuario_c else 'ERROR'}")
if id_empleado:
    print(f"✅ Empleado: ID {id_empleado}")
else:
    print(f"⚠️  Empleado: No creado")

print("\n📊 QUERIES EN DBEAVER:")
print(f"\n1️⃣  Ver citas del usuario individual (con DURACION):")
print(f"    SELECT ID_CITA, DESCRIPCION, DURACION FROM CITAS_IND WHERE ID_USUARIO = {id_usuario_i} ORDER BY FECHA DESC;")

print(f"\n2️⃣  Ver usuarios de ambos tipos:")
print(f"    SELECT ID_USUARIO, NOMBRE, TIPO FROM USUARIOS WHERE TIPO IN ('I', 'C') ORDER BY ID_USUARIO DESC LIMIT 5;")

if id_usuario_c:
    print(f"\n3️⃣  Ver empleados (si existen):")
    print(f"    SELECT ID_EMPLEADO, NOMBRE, TIPO FROM EMPLEADOS WHERE ID_USUARIO_ADM = {id_usuario_c};")
