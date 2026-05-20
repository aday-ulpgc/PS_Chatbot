from src.nlp.gemini_service import NLPService


def test_reparar_json_completo():
    # JSON completo ya válido
    json_valido = '{"accion": "cancelar", "estado": "listo_para_cancelar"}'
    assert NLPService._reparar_json(json_valido) == json_valido


def test_reparar_json_truncado_llaves():
    # JSON truncado sin llaves
    json_truncado = '{"accion": "cancelar", "estado": "listo_para_cancelar"'
    resultado = NLPService._reparar_json(json_truncado)
    assert resultado == '{"accion": "cancelar", "estado": "listo_para_cancelar"}'


def test_reparar_json_coma_colgante():
    # JSON truncado con coma colgante
    json_truncado = '{"accion": "cancelar", "estado": "listo_para_cancelar",'
    resultado = NLPService._reparar_json(json_truncado)
    assert resultado == '{"accion": "cancelar", "estado": "listo_para_cancelar"}'


def test_reparar_json_string_incompleto():
    # JSON truncado dentro de un string de valor
    json_truncado = '{"accion": "cancelar", "estado": "list'
    resultado = NLPService._reparar_json(json_truncado)
    assert resultado == '{"accion": "cancelar", "estado": "list"}'


def test_limpiar_json_robustez():
    # Simular una respuesta completa con texto markdown y JSON truncado
    respuesta = 'Aquí tienes el JSON solicitado:\n```json\n{\n  "accion": "cancelar",\n  "estado": "listo_para_cancelar",\n'
    resultado = NLPService._limpiar_json(respuesta)
    assert resultado == {"accion": "cancelar", "estado": "listo_para_cancelar"}
