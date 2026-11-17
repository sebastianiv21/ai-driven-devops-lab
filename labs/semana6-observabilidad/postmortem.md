# Postmortem corto — orders-api, 20 de septiembre de 2026

**Estado:** causa raíz probable, no confirmada (solo se tiene el log del servicio).
**Evidencia:** `logs/orders-api.log` (155 líneas, 08:00:13–08:36). Verificación manual en
`bitacora/evidencia/semana6/01-verificacion-manual.txt`.

## Qué pasó
`POST /orders/quote` devolvió HTTP 500 en 35 requests consecutivos, todos con
`DatabaseTimeoutError: connection pool exhausted`. El servicio se recuperó solo, sin
intervención registrada en el log.

## Cuándo
| Momento | Hora (log, sin zona horaria) |
|---|---|
| Último 200 antes del incidente | 08:21:36 |
| Primer 500 | 08:21:57 |
| Último 500 | 08:24:07 |
| Primer 200 después | 08:24:41 |

Duración con errores: **~2 min 10 s** (~3 min contando hasta el primer request sano).

## Impacto
- 35 de 35 requests fallaron entre 08:21:57 y 08:24:07: **100 % de error** en el endpoint
  durante la ventana; 35/155 (22,6 %) en toda la mañana registrada.
- Latencia: base de 20–90 ms (promedio por minuto 20–76 ms) → **816–2.339 ms** durante el
  incidente. Los requests fallidos tardan lo que tarda el timeout de espera del pool.
- Clientes afectados: no se puede saber (el log no tiene ID de cliente ni de request).

## Señal adicional
El volumen subió de 3–5 requests/min a **15 requests/min** en 08:22 y 08:23 y volvió a 3–4
cuando el error desapareció. Con este log no se puede distinguir si fue la **causa** (pico de
tráfico que agotó el pool) o el **efecto** (clientes reintentando tras recibir 500).

## Causa probable
Saturación del pool de conexiones a la base de datos: todas las conexiones ocupadas y los
requests nuevos esperan hasta el timeout. Hipótesis, de más a menos probable:

1. **Pico de carga o tormenta de reintentos** que supera el tamaño del pool. Coincide con el
   volumen ×4 y con la recuperación espontánea al bajar la carga.
2. **Queries lentas** que retienen conexiones (lock, tabla sin índice, BD degradada). Compatible
   con todo, pero el log no muestra tiempos de query.
3. ~~Fuga de conexiones~~ (conexiones que nunca se devuelven): **poco probable**, porque una fuga
   no se recupera sola sin reiniciar el proceso, y aquí se recuperó en ~2 min.

## Evidencia que pediría antes de actuar
- Métricas del pool (conexiones activas / ociosas / en espera, tamaño máximo) y de la BD
  (conexiones totales, CPU, `pg_stat_activity` o equivalente, slow query log, locks).
- Tráfico por cliente / IP / user-agent en el load balancer, para separar pico real de reintentos.
- Deploys, cambios de configuración o feature flags alrededor de las 08:20.
- Actividad del worker u otros consumidores de la misma BD en esa ventana (jobs batch, backups).
- Trazas de requests lentos, para ver en qué paso se pierde el tiempo.

## Acciones sugeridas
- Alertar por tasa de 5xx y por "pool en espera > 0 durante N s", no solo por latencia genérica.
- Registrar `request_id` y cliente en cada línea del log.
- Revisar el tamaño del pool contra las conexiones máximas de la BD y el número de réplicas.
- Clientes con reintentos con backoff exponencial y jitter, para no amplificar el incidente.
- Runbook para este tipo de incidente: ver Semana 7.
