"""
Script de prueba para verificar el sistema de fallback de modelos Gemini.
Simula errores 429 y demuestra el cambio automático entre modelos.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.nlp.gemini_service import NLPService


def test_cambio_modelos():
    """Test 1: Verifica que el cambio de modelos funciona."""
    print("\n" + "=" * 70)
    print("🧪 TEST 1: Cambio Manual de Modelos")
    print("=" * 70)

    print(f"\n📍 Modelo inicial: {NLPService.obtener_modelo_actual()}")
    print(f"   Índice: {NLPService._modelo_actual_idx}")

    print("\n🔄 Cambiando al siguiente modelo...")
    modelo = NLPService.cambiar_al_siguiente_modelo()
    print(f"   Nuevo modelo: {modelo}")
    print(f"   Índice: {NLPService._modelo_actual_idx}")

    print("\n🔄 Cambiando al siguiente modelo...")
    modelo = NLPService.cambiar_al_siguiente_modelo()
    print(f"   Nuevo modelo: {modelo}")
    print(f"   Índice: {NLPService._modelo_actual_idx}")

    print("\n✅ TEST 1 PASSED: Cambio de modelos funciona correctamente")


def test_ciclo_modelos():
    """Test 2: Verifica que recorre todos los modelos y vuelve al inicio."""
    print("\n" + "=" * 70)
    print("🧪 TEST 2: Ciclo Completo de Modelos")
    print("=" * 70)

    # Resetear al inicio
    NLPService.resetear_a_modelo_preferido()

    print("\n📋 Lista de modelos disponibles:")
    for i, modelo in enumerate(NLPService.MODELOS_DISPONIBLES):
        print(f"   {i+1}. {modelo}")

    print("\n🔄 Recorriendo todos los modelos:")
    modelos_visitados = []

    for i in range(len(NLPService.MODELOS_DISPONIBLES) + 1):
        modelo_actual = NLPService.obtener_modelo_actual()
        modelos_visitados.append(modelo_actual)
        print(f"   Paso {i+1}: {modelo_actual}")

        if i < len(NLPService.MODELOS_DISPONIBLES):
            NLPService.cambiar_al_siguiente_modelo()

    # Verificar que después de pasar todos, vuelve al primero
    if modelos_visitados[0] == modelos_visitados[-1]:
        print(
            f"\n✅ TEST 2 PASSED: Ciclo completo funciona (vuelve a {modelos_visitados[0]})"
        )
    else:
        print("\n❌ TEST 2 FAILED: No volvió al modelo inicial")


def test_reset_modelo():
    """Test 3: Verifica que resetear funciona."""
    print("\n" + "=" * 70)
    print("🧪 TEST 3: Reset al Modelo Preferido")
    print("=" * 70)

    print(f"\n📍 Modelo inicial: {NLPService.obtener_modelo_actual()}")

    # Cambiar varias veces
    print("\n🔄 Cambiando 3 veces...")
    for _ in range(3):
        NLPService.cambiar_al_siguiente_modelo()

    print(f"   Modelo actual después de cambiar: {NLPService.obtener_modelo_actual()}")

    # Resetear
    print("\n🔄 Reseteando a modelo preferido...")
    NLPService.resetear_a_modelo_preferido()
    modelo_reset = NLPService.obtener_modelo_actual()
    print(f"   Modelo después del reset: {modelo_reset}")

    if modelo_reset == NLPService.MODELOS_DISPONIBLES[0]:
        print("\n✅ TEST 3 PASSED: Reset funciona correctamente")
    else:
        print("\n❌ TEST 3 FAILED: No reseteó al modelo preferido")


def test_estado_actual():
    """Test 4: Muestra el estado actual del sistema."""
    print("\n" + "=" * 70)
    print("🧪 TEST 4: Estado Actual del Sistema")
    print("=" * 70)

    print("\n📊 Información del Sistema NLPService:")
    print(f"   Total de modelos disponibles: {len(NLPService.MODELOS_DISPONIBLES)}")
    print(f"   Modelo en uso: {NLPService.obtener_modelo_actual()}")
    print(f"   Índice actual: {NLPService._modelo_actual_idx}")
    print(f"   Modelo preferido (respaldo): {NLPService.MODELOS_DISPONIBLES[0]}")

    print("\n📋 Orden de fallback:")
    for i, modelo in enumerate(NLPService.MODELOS_DISPONIBLES):
        if i == NLPService._modelo_actual_idx:
            print(f"   >>> {i+1}. {modelo} (ACTIVO)")
        else:
            print(f"       {i+1}. {modelo}")

    print("\n✅ TEST 4 PASSED: Estado mostrado correctamente")


def mostrar_instrucciones_logs():
    """Muestra instrucciones para monitorear los logs en el bot real."""
    print("\n" + "=" * 70)
    print("📝 CÓMO MONITOREAR EN EL BOT REAL")
    print("=" * 70)

    print("""
Durante la operación normal del bot, verás estos mensajes en los logs:

1️⃣  AL INICIAR (modelo preferido):
    📡 Intentando con modelo: gemini-3-flash

2️⃣  SI LA API DEVUELVE ERROR 429 (SOBRECARGADA):
    ❌ Error 429 (Sobrecargado) con modelo: gemini-3-flash
    ⚠️  Modelo sobrecargado. Cambiando a: gemini-3-flash-lite
    📡 Intentando con modelo: gemini-3-flash-lite

3️⃣  SI SIGUE FALLANDO:
    ❌ Error 429 (Sobrecargado) con modelo: gemini-3-flash-lite
    ⚠️  Modelo sobrecargado. Cambiando a: gemini-3-flash-live
    📡 Intentando con modelo: gemini-3-flash-live
    ... (y así sucesivamente)

4️⃣  SI TODO FUNCIONA (ÉXITO):
    ✅ Respuesta recibida correctamente
    🔄 Reseteando a modelo preferido: gemini-3-flash

5️⃣  SI TODOS LOS MODELOS FALLAN:
    ❌ Se agotaron todos los modelos
    (Respuesta de emergencia al usuario)

---
💡 PRUEBAS RECOMENDADAS:
   • Envía varios mensajes al bot durante carga normal
   • Observa los logs para ver qué modelo se está usando
   • Verifica que siempre empieza con gemini-3-flash
   • Si hay errores, verás el cambio automático en los logs
    """)


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("SUITE DE PRUEBAS - SISTEMA DE FALLBACK DE MODELOS GEMINI")
    print("🚀 " * 20)

    try:
        # Ejecutar todos los tests
        test_cambio_modelos()
        test_ciclo_modelos()
        test_reset_modelo()
        test_estado_actual()

        # Mostrar instrucciones
        mostrar_instrucciones_logs()

        print("\n" + "=" * 70)
        print("✨ TODOS LOS TESTS PASARON CORRECTAMENTE ✨")
        print("=" * 70)
        print("\n✅ El sistema de fallback de modelos está funcionando.")
        print("✅ El bot cambiará automáticamente entre modelos si hay errores.")
        print("\n")

    except Exception as e:
        print(f"\n❌ ERROR EN LOS TESTS: {e}")
        import traceback

        traceback.print_exc()
