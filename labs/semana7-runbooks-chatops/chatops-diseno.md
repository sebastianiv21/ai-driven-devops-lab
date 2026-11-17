# Diseño ChatOps — runbook "connection pool exhausted" (conceptual)

## Flujo en Slack
```
Ingeniero:  /runbook connection-pool orders-api
Bot:        🔎 Diagnóstico (solo lectura) — 15 min
            • 35 errores "pool exhausted" desde 08:21:57
            • tráfico 15 req/min (base 3–5) → probable pico o reintentos
            • 0 deploys en la última hora · 2/2 pods Ready
            • BD: 20/20 conexiones activas, query más vieja 0,4 s
            Clasificación sugerida: pico de tráfico / reintentos
            Acciones propuestas:
              [Escalar a 4 réplicas]  [Cancelar query pid…]  [Reiniciar deployment]
Ingeniero:  (clic en "Escalar a 4 réplicas")
Bot:        ⏸ Requiere aprobación de un segundo ingeniero de on-call.
On-call #2: (aprueba)
Bot:        ✅ orders-api escalado a 4 réplicas por @ing1, aprobado por @ing2 — registrado en el incidente.
```

## Qué hace el bot solo vs. con aprobación
| Acción | Autonomía | Por qué |
|---|---|---|
| Leer logs, métricas, `pg_stat_activity`, historial de deploys | Automática | Solo lectura, sin riesgo, es lo que más tiempo ahorra |
| Clasificar el incidente y sugerir el paso del runbook | Automática | Es una sugerencia; el humano decide |
| Publicar resumen en el canal del incidente | Automática | Comunicación, reversible |
| Escalar réplicas dentro de un límite predefinido | 1 aprobación humana | Cambia producción y puede empeorar la presión sobre la BD |
| Reiniciar deployment, cancelar queries | Aprobación de 2 personas | Corta requests en curso; error humano costoso |
| Cambiar config de la BD, borrar datos, rollback de esquema | Fuera del bot | Requiere DBA y su propio procedimiento |

## Dónde está el límite de autonomía y por qué
El bot **observa, resume y propone**; **no muta producción sin una persona** que apruebe con
su identidad. Es el mismo criterio que el agente de reintentos de la Semana 5:

- Actúa solo cuando la acción es reversible y de bajo impacto (re-encolar una orden / leer métricas).
- Se detiene y escala cuando la acción es destructiva o cuando la situación parece sistémica
  (el circuit breaker del agente ↔ "BD no responde" aquí).
- Todo queda auditado: quién pidió, quién aprobó, qué se ejecutó.

Guardrails técnicos: el bot corre con un service account de solo lectura; las acciones de
escritura usan un rol distinto que se asume solo tras la aprobación; los comandos permitidos
son una lista cerrada (no shell libre); los secretos nunca se imprimen en el canal.
