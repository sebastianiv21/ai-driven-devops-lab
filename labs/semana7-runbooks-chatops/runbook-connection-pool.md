# Runbook — orders-api: "connection pool exhausted"

**Servicio:** orders-api · **Severidad típica:** SEV2 (checkout de cotizaciones caído)
**Origen:** incidente del 20-sep, ver `labs/semana6-observabilidad/postmortem.md`.

## 1. Síntomas (cómo se detecta)
- Alerta de tasa de 5xx en `POST /orders/quote` o de latencia p95 > 1 s.
- Logs con `status=500` y `error="DatabaseTimeoutError: connection pool exhausted"`.
- Latencia de los requests fallidos ≈ timeout de espera del pool (0,8–2,3 s en el incidente
  original), muy por encima de la base de 20–90 ms.

## 2. Diagnóstico rápido (solo lectura, primeros 5 minutos)
```bash
# ¿Cuántos errores y desde cuándo?
kubectl -n orders logs deploy/orders-api --since=15m | grep -c 'connection pool exhausted'
kubectl -n orders logs deploy/orders-api --since=15m | grep 'status=500' | head -1

# ¿Cambió algo? (deploy reciente, réplicas, reinicios)
kubectl -n orders rollout history deploy/orders-api
kubectl -n orders get pods -l app=orders-api -o wide

# ¿Subió el tráfico? Comparar requests/min con la base (3–5/min en el incidente original).
kubectl -n orders logs deploy/orders-api --since=15m | cut -c1-16 | sort | uniq -c
```
```sql
-- En la BD (Postgres): conexiones por estado y queries más viejas en curso
SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'orders' GROUP BY state;
SELECT pid, now() - query_start AS duracion, state, left(query, 80)
FROM pg_stat_activity WHERE datname = 'orders' AND state <> 'idle'
ORDER BY duracion DESC LIMIT 10;
```
**Clasificar según lo que se ve:**

| Observación | Tipo probable |
|---|---|
| Requests/min ×3 o más, queries rápidas | Pico de tráfico o tormenta de reintentos |
| Pocas queries con duración de segundos/minutos, `idle in transaction` | Query lenta o lock |
| Conexiones activas crecen sin bajar aunque baje el tráfico | Fuga de conexiones |
| La BD no responde o CPU al 100 % | BD degradada: escalar a DBA |

## 3. Mitigación inmediata (aliviar el síntoma, no es el fix)
- **Pico/reintentos:** escalar réplicas solo si `réplicas × pool_size` queda por debajo de
  `max_connections` de la BD; si no, aplicar rate limiting en el gateway.
  *Requiere aprobación humana* (cambia producción y puede aumentar la presión sobre la BD).
- **Query lenta o lock:** cancelar la query identificada (`SELECT pg_cancel_backend(<pid>);`).
  *Requiere aprobación humana.*
- **Fuga:** reinicio progresivo del deployment (`kubectl -n orders rollout restart deploy/orders-api`)
  para liberar conexiones. *Requiere aprobación humana.*
- Comunicar en el canal del incidente: inicio, impacto observado, mitigación aplicada.

## 4. Causa raíz probable y cómo confirmarla
| Hipótesis | Confirmación |
|---|---|
| Pico de tráfico / reintentos | Tráfico por cliente en el load balancer; ¿un cliente concentra los requests? |
| Query lenta / lock | `pg_stat_activity`, `pg_locks`, slow query log en la ventana del incidente |
| Fuga de conexiones | Conexiones activas vs. tráfico en el tiempo; revisar código que abre conexiones sin cerrarlas |
| Pool mal dimensionado | Comparar pool_size × réplicas contra la carga normal del servicio |

## 5. Solución definitiva (según la causa)
- Reintentos de clientes con backoff exponencial + jitter; circuit breaker en el cliente.
- Índice o reescritura de la query lenta; timeouts de statement en la BD.
- Cerrar conexiones con context managers / `finally`; test que lo cubra.
- Ajustar `pool_size` y `pool_timeout`; considerar PgBouncer si hay muchas réplicas.
- Alertas: 5xx > 5 % por 2 min, y "requests esperando conexión" > 0 por 1 min.

## 6. Cuándo escalar a un humano / dejar el runbook
- Los errores siguen después de 15 minutos de mitigación.
- La BD no responde, está al límite de CPU/disco o hay que tocar su configuración.
- Cualquier acción que borre o modifique datos, o reinicie la BD.
- El incidente afecta a otros servicios que comparten la misma BD.
- Hay señales de abuso (un solo cliente/IP genera el pico): involucrar a seguridad.
