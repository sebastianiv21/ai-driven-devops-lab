"""
Agente simple de reintentos para "Orders API".

Revisa la cola de órdenes (app/worker/queue.json). Las órdenes "failed" con menos de
MAX_RETRIES intentos se vuelven a encolar ("pending") para que el worker las procese;
las que ya llegaron al límite se escalan a un humano ("needs_human").

Límites de autonomía:
- Solo re-encola: no procesa órdenes, no las borra, no cambia montos.
- Nunca reintenta más allá de MAX_RETRIES: a partir de ahí decide un humano.
- Circuit breaker: si hay más de MAX_ACTIONS_PER_RUN fallas a la vez, asume un problema
  sistémico (BD caída, dependencia rota) y no toca nada; reintentar en masa solo
  sumaría carga al incidente.
- --dry-run muestra lo que haría sin escribir la cola.
- Cada acción queda registrada en stdout con timestamp (auditoría).

Uso: python agente_esqueleto.py [--dry-run] [ruta/a/queue.json]
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

QUEUE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "app", "worker", "queue.json")
MAX_RETRIES = 3
MAX_ACTIONS_PER_RUN = 20


def log(mensaje):
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} [agente] {mensaje}")


def load_queue(path=QUEUE_FILE):
    # Sin archivo no hay órdenes que revisar: no es un error, el worker aún no creó la cola.
    # Un JSON corrupto sí es un error: se propaga para no sobrescribir datos que no entendimos.
    if not os.path.exists(path):
        log(f"no existe la cola {path}; nada que hacer")
        return []
    with open(path) as f:
        return json.load(f)


def save_queue(orders, path=QUEUE_FILE):
    # Escritura atómica: si el proceso muere a mitad, la cola original queda intacta.
    directorio = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", dir=directorio, delete=False, suffix=".tmp") as tmp:
        try:
            json.dump(orders, tmp, indent=2)
            tmp.write("\n")
        except Exception:
            tmp.close()
            os.unlink(tmp.name)
            raise
    # NamedTemporaryFile crea el archivo con 0600; el worker puede correr con otro usuario.
    os.chmod(tmp.name, 0o644)
    os.replace(tmp.name, path)


def needs_retry(order):
    return order.get("status") == "failed" and order.get("attempts", 0) < MAX_RETRIES


def is_exhausted(order):
    return order.get("status") == "failed" and order.get("attempts", 0) >= MAX_RETRIES


def retry_order(order):
    order["attempts"] = order.get("attempts", 0) + 1
    order["status"] = "pending"
    log(f"{order['id']}: re-encolada (intento {order['attempts']}/{MAX_RETRIES})")


def escalate_order(order):
    order["status"] = "needs_human"
    log(f"{order['id']}: {order['attempts']} intentos agotados -> escalada a un humano")


def run_agent(path=QUEUE_FILE, dry_run=False):
    orders = load_queue(path)
    a_reintentar = [o for o in orders if needs_retry(o)]
    a_escalar = [o for o in orders if is_exhausted(o)]
    resumen = {"reintentadas": [], "escaladas": [], "abortado": False}

    if len(a_reintentar) + len(a_escalar) > MAX_ACTIONS_PER_RUN:
        log(f"ALERTA: {len(a_reintentar) + len(a_escalar)} órdenes fallidas (> {MAX_ACTIONS_PER_RUN}). "
            "Posible falla sistémica: no se reintenta nada, requiere revisión humana.")
        resumen["abortado"] = True
        return resumen

    for order in a_reintentar:
        retry_order(order)
        resumen["reintentadas"].append(order["id"])
    for order in a_escalar:
        escalate_order(order)
        resumen["escaladas"].append(order["id"])

    if dry_run:
        log("dry-run: la cola NO se modificó")
    elif resumen["reintentadas"] or resumen["escaladas"]:
        save_queue(orders, path)

    log(f"resumen: {resumen}")
    return resumen


if __name__ == "__main__":
    args = sys.argv[1:]
    dry = "--dry-run" in args
    rutas = [a for a in args if a != "--dry-run"]
    resultado = run_agent(rutas[0] if rutas else QUEUE_FILE, dry_run=dry)
    # Código de salida != 0 para que cron/CI lo trate como alerta, no como corrida exitosa.
    sys.exit(2 if resultado["abortado"] else 0)
