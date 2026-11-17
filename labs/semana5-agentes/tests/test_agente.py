"""
Tests del agente de reintentos (Semana 5).
Ejecuta: python -m pytest labs/semana5-agentes/tests/ -v
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agente_esqueleto as agente

EJEMPLO = os.path.join(os.path.dirname(__file__), "..", "queue-ejemplo.json")


@pytest.fixture
def cola(tmp_path):
    """Copia la cola de ejemplo a un archivo temporal para no tocar la real."""
    destino = tmp_path / "queue.json"
    with open(EJEMPLO) as f:
        destino.write_text(f.read())
    return destino


def leer(path):
    return {o["id"]: o for o in json.loads(path.read_text())}


def test_cola_inexistente_no_es_error(tmp_path):
    assert agente.load_queue(tmp_path / "no-existe.json") == []


def test_json_corrupto_falla_ruidosamente(tmp_path):
    roto = tmp_path / "queue.json"
    roto.write_text("{no es json")
    with pytest.raises(json.JSONDecodeError):
        agente.load_queue(roto)


@pytest.mark.parametrize(
    "orden, esperado",
    [
        ({"status": "completed", "attempts": 0}, False),
        ({"status": "pending", "attempts": 0}, False),
        ({"status": "failed", "attempts": 1}, True),
        ({"status": "failed", "attempts": 2}, True),
        ({"status": "failed", "attempts": 3}, False),
        ({"status": "failed"}, True),  # sin campo attempts = 0 intentos
    ],
)
def test_needs_retry(orden, esperado):
    assert agente.needs_retry(orden) is esperado


def test_run_agent_sobre_la_cola_de_ejemplo(cola):
    resumen = agente.run_agent(cola)
    ordenes = leer(cola)

    assert ordenes["ORD-1001"]["status"] == "completed"   # no se toca
    assert ordenes["ORD-1004"]["status"] == "pending"     # no se toca
    # Reintento: se vuelve a encolar para el worker y suma un intento.
    assert ordenes["ORD-1002"] == {"id": "ORD-1002", "status": "pending", "attempts": 2}
    # En el límite: no se reintenta más, se escala a un humano.
    assert ordenes["ORD-1003"]["status"] == "needs_human"
    assert ordenes["ORD-1003"]["attempts"] == 3

    assert resumen == {"reintentadas": ["ORD-1002"], "escaladas": ["ORD-1003"], "abortado": False}


def test_dry_run_no_modifica_la_cola(cola):
    antes = cola.read_text()
    resumen = agente.run_agent(cola, dry_run=True)
    assert cola.read_text() == antes
    assert resumen["reintentadas"] == ["ORD-1002"]
    assert resumen["escaladas"] == ["ORD-1003"]


def test_sin_acciones_no_reescribe_la_cola(tmp_path):
    cola = tmp_path / "queue.json"
    cola.write_text('[{"id": "ORD-1", "status": "completed", "attempts": 0}]')
    mtime = os.stat(cola).st_mtime_ns
    agente.run_agent(cola)
    assert os.stat(cola).st_mtime_ns == mtime


def test_circuit_breaker_no_se_activa_en_el_limite(tmp_path):
    """Exactamente MAX_ACTIONS_PER_RUN fallas todavía se procesan."""
    cola = tmp_path / "queue.json"
    fallas = [{"id": f"ORD-{i}", "status": "failed", "attempts": 0} for i in range(agente.MAX_ACTIONS_PER_RUN)]
    cola.write_text(json.dumps(fallas))

    resumen = agente.run_agent(cola)

    assert resumen["abortado"] is False
    assert len(resumen["reintentadas"]) == agente.MAX_ACTIONS_PER_RUN


def test_cli_sale_con_error_si_el_circuit_breaker_se_activa(tmp_path):
    import subprocess
    cola = tmp_path / "queue.json"
    fallas = [{"id": f"ORD-{i}", "status": "failed", "attempts": 0} for i in range(agente.MAX_ACTIONS_PER_RUN + 1)]
    cola.write_text(json.dumps(fallas))
    script = os.path.join(os.path.dirname(__file__), "..", "agente_esqueleto.py")
    resultado = subprocess.run([sys.executable, script, str(cola)], capture_output=True, text=True)
    assert resultado.returncode == 2
    assert "ALERTA" in resultado.stdout


def test_escritura_conserva_permisos_legibles(cola):
    agente.run_agent(cola)
    assert os.stat(cola).st_mode & 0o777 == 0o644
    assert not list(cola.parent.glob("*.tmp"))  # sin archivos temporales huérfanos


def test_circuit_breaker_con_demasiadas_fallas(tmp_path):
    """Muchas fallas a la vez sugieren un problema sistémico: no reintentar en masa."""
    cola = tmp_path / "queue.json"
    fallas = [{"id": f"ORD-{i}", "status": "failed", "attempts": 0} for i in range(agente.MAX_ACTIONS_PER_RUN + 1)]
    cola.write_text(json.dumps(fallas))

    resumen = agente.run_agent(cola)

    assert resumen["abortado"] is True
    assert resumen["reintentadas"] == []
    assert json.loads(cola.read_text()) == fallas  # nada cambió
