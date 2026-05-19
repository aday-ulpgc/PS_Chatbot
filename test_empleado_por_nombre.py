#!/usr/bin/env python3
"""Test para obtener_empleado_por_nombre()"""

from src.BBDD.databasecontroller import (
    get_db,
    crear_usuario,
    crear_empleado,
    obtener_empleado_por_nombre,
    init_db,
)

# Inicializar BD
init_db()

db_gen = get_db()
session = next(db_gen)

try:
    try:
        # Crear usuario corporativo
        print("📝 Creando usuario corporativo...")
        usuario = crear_usuario(
            session,
            email="admin_test@corp.com",
            tipo="C",
            nombre="Admin Test",
            contrasena_corp="password123",
        )
        print(f"   ✅ Usuario creado - ID: {usuario.ID_USUARIO}")

        # Crear empleados
        print("\n👔 Creando empleados...")
        emp1 = crear_empleado(
            session,
            usuario.ID_USUARIO,
            tipo="senior",
            nombre="Juan Pérez",
            contrasena_corp="pass1",
            id_admin=None,
        )
        print(f"   ✅ Empleado 1 - ID: {emp1.ID_EMPLEADO}, Nombre: {emp1.NOMBRE}")

        emp2 = crear_empleado(
            session,
            usuario.ID_USUARIO,
            tipo="junior",
            nombre="María García",
            contrasena_corp="pass2",
            id_admin=None,
        )
        print(f"   ✅ Empleado 2 - ID: {emp2.ID_EMPLEADO}, Nombre: {emp2.NOMBRE}")

        # Pruebas de búsqueda
        print("\n🔍 Pruebas de búsqueda por nombre:")

        # Test 1: Búsqueda exacta (case-insensitive)
        print("\n   Test 1: Búsqueda 'juan pérez' (minúsculas)...")
        resultado = obtener_empleado_por_nombre(session, "juan pérez")
        assert resultado is not None, "❌ Debería encontrar el empleado"
        assert resultado.ID_EMPLEADO == emp1.ID_EMPLEADO, "❌ ID no coincide"
        print(f"      ✅ Encontrado: {resultado.NOMBRE} (ID: {resultado.ID_EMPLEADO})")

        # Test 2: Búsqueda con mayúsculas
        print("\n   Test 2: Búsqueda 'MARÍA GARCÍA' (mayúsculas)...")
        resultado = obtener_empleado_por_nombre(session, "MARÍA GARCÍA")
        assert resultado is not None, "❌ Debería encontrar el empleado"
        assert resultado.ID_EMPLEADO == emp2.ID_EMPLEADO, "❌ ID no coincide"
        print(f"      ✅ Encontrado: {resultado.NOMBRE} (ID: {resultado.ID_EMPLEADO})")

        # Test 3: Búsqueda parcial (si solo usamos first() y la búsqueda es exacta)
        print("\n   Test 3: Búsqueda 'Juan' (nombre parcial - solo si coincide)...")
        resultado = obtener_empleado_por_nombre(session, "juan")
        if resultado:
            print(
                f"      ⚠️ Búsqueda parcial NO soportada (requiere nombre completo): {resultado.NOMBRE}"
            )
        else:
            print("      ℹ️ Búsqueda 'juan' no encontrada (búsqueda exacta activada)")

        # Test 4: No encontrado
        print("\n   Test 4: Búsqueda 'Pedro López' (no existe)...")
        resultado = obtener_empleado_por_nombre(session, "Pedro López")
        assert resultado is None, "❌ No debería encontrar nada"
        print("      ✅ Correctamente no encontrado")

        print("\n" + "=" * 50)
        print("✅ Todos los tests pasaron correctamente")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

finally:
    # Limpiar
    try:
        next(db_gen)
    except StopIteration:
        pass
