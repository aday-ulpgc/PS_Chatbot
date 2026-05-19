#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar:
1. Los empleados se crearon correctamente
2. Se puede crear un cliente
3. Se puede crear una cita vinculada a empleado
4. Se muestran los datos correctamente
"""

import sys
import os
from datetime import datetime, timedelta
from pprint import pprint

# Agregar src al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.BBDD.database_service import (
    obtener_empleados_activos,
    obtener_o_crear_cliente_por_telegram,
    guardar_cita_en_db,
)
from src.BBDD.databasecontroller import get_session, CitaCorp, Empleado, Cliente


def test_empleados():
    """Test 1: Verificar que los empleados existen"""
    print("\n" + "=" * 60)
    print("TEST 1: Obtener Empleados Activos")
    print("=" * 60)

    empleados = obtener_empleados_activos()

    if not empleados:
        print("No se encontraron empleados")
        return False

    print(f"\nSe encontraron {len(empleados)} empleados:\n")
    for emp in empleados:
        print(f"   ID: {emp['ID_EMPLEADO']}")
        print(f"   Nombre: {emp['NOMBRE']}")
        print(f"   Email: {emp['EMAIL']}")
        print()

    return empleados


def test_crear_cliente(empleados):
    """Test 2: Crear un cliente de prueba"""
    print("\n" + "=" * 60)
    print("TEST 2: Crear Cliente de Prueba")
    print("=" * 60)

    telegram_id = 123456789
    nombre = "Cliente Test"

    # Usar el primer empleado (Raul, ID 7)
    empleado_id = empleados[0]["ID_EMPLEADO"]
    print(
        f"\nCreando cliente para el empleado: {empleados[0]['NOMBRE']} (ID: {empleado_id})"
    )

    cliente_result = obtener_o_crear_cliente_por_telegram(
        telegram_id=telegram_id, nombre=nombre, id_empleado_default=empleado_id
    )

    print(f"\nResultado:")
    pprint(cliente_result)

    if cliente_result.get("error"):
        print(f"Error: {cliente_result.get('error')}")
        return None

    cliente_id = cliente_result.get("cliente_id")
    print(f"Cliente creado/obtenido con ID: {cliente_id}")

    return cliente_id


def test_crear_cita(empleado_id, empleado_nombre, cliente_id):
    """Test 3: Crear una cita y vincularla con empleado"""
    print("\n" + "=" * 60)
    print("TEST 3: Crear Cita Vinculada a Empleado")
    print("=" * 60)

    fecha = datetime.now() + timedelta(days=1)
    descripcion = "Cita de prueba desde script"

    print(f"\nDatos de la cita:")
    print(f"   Empleado: {empleado_nombre} (ID: {empleado_id})")
    print(f"   ID Cliente: {cliente_id}")
    print(f"   Fecha: {fecha}")
    print(f"   Descripcion: {descripcion}")

    success = guardar_cita_en_db(
        id_empleado=empleado_id,
        id_cliente=cliente_id,
        fecha=fecha,
        descripcion=descripcion,
        duracion=60,
    )

    if success:
        print(f"\nCita creada exitosamente")
        return True
    else:
        print(f"\nError al crear cita")
        return False


def test_leer_cita_desde_bd(cliente_id, empleado_id):
    """Test 4: Leer la cita desde la BD y mostrar datos completos"""
    print("\n" + "=" * 60)
    print("TEST 4: Leer Cita y Mostrar Datos del Empleado")
    print("=" * 60)

    try:
        with get_session() as session:
            # Obtener las citas del cliente
            citas = (
                session.query(CitaCorp)
                .filter(CitaCorp.ID_CLIENTE == cliente_id, CitaCorp.ELIMINADO == None)
                .all()
            )

            if not citas:
                print("❌ No se encontraron citas para este cliente")
                return False

            print(f"\n✅ Se encontraron {len(citas)} cita(s):\n")

            for cita in citas:
                print(f"   ID Cita: {cita.ID_CITA}")
                print(f"   Fecha: {cita.FECHA}")
                print(f"   Descripción: {cita.DESCRIPCION}")
                print(f"   Duración: {cita.DURACION} minutos")

                # Mostrar datos del empleado
                if cita.empleado:
                    print(f"\n   [EMPLEADO] Datos del Empleado:")
                    print(f"      ID: {cita.empleado.ID_EMPLEADO}")
                    print(f"      Nombre: {cita.empleado.NOMBRE}")
                    print(f"      Email: {cita.empleado.EMAIL}")

                # Mostrar datos del cliente
                if cita.cliente:
                    print(f"\n   [CLIENTE] Datos del Cliente:")
                    print(f"      ID: {cita.cliente.ID_CLIENTE}")
                    print(f"      Nombre: {cita.cliente.NOMBRE}")
                    print(f"      Telegram ID: {cita.cliente.TELEGRAM_ID}")

                print()

            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("PRUEBA COMPLETA: CITAS CON EMPLEADOS".center(60))
    print("=" * 60)

    # Test 1: Obtener empleados
    empleados = test_empleados()
    if not empleados or len(empleados) == 0:
        print("No hay empleados para continuar las pruebas")
        return

    # Test 2: Crear cliente
    cliente_id = test_crear_cliente(empleados)
    if not cliente_id:
        print("No se pudo crear cliente")
        return

    # Test 3: Crear cita
    empleado_id = empleados[0]["ID_EMPLEADO"]
    empleado_nombre = empleados[0]["NOMBRE"]
    success = test_crear_cita(empleado_id, empleado_nombre, cliente_id)
    if not success:
        print("No se pudo crear cita")
        return

    # Test 4: Leer cita con datos del empleado
    test_leer_cita_desde_bd(cliente_id, empleado_id)

    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS".center(60))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
