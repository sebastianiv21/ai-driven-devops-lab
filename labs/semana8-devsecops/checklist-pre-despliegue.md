# Checklist — antes de desplegar a producción

Reutilizable para cualquier servicio. Cada punto debería poder verificarse con un comando o
un escáner, no "a ojo".

## Secretos
- [ ] No hay credenciales, tokens ni URLs internas en el YAML, Dockerfile, código ni historial de git.
- [ ] Los secretos vienen de un `Secret` creado fuera de git (External Secrets / Sealed Secrets / vault).
- [ ] Si un secreto llegó a un commit: **rotarlo** primero (borrarlo del archivo no basta).
- [ ] El escáner de secretos corre en CI — y se sabe qué patrones no detecta (ver nota).

## Imagen
- [ ] Base mínima (`-slim`/distroless) con versión fija; idealmente digest `@sha256`.
- [ ] `USER` no-root con UID fijo (≥ 10000).
- [ ] Solo se copian los archivos necesarios (o hay `.dockerignore`).
- [ ] Dependencias instaladas en el build (la imagen arranca sin pasos manuales).
- [ ] Servidor de aplicación de producción (gunicorn/uvicorn), no el servidor de desarrollo del
      framework (`app.run()` de Flask, como hace todavía `Dockerfile-seguro` en este lab).
- [ ] `trivy image` sin vulnerabilidades CRITICAL/HIGH con fix disponible.

## Manifiesto Kubernetes
- [ ] Namespace propio, no `default`.
- [ ] Imagen con tag inmutable, nunca `:latest`.
- [ ] `privileged: false`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`.
- [ ] `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `seccompProfile: RuntimeDefault`.
- [ ] `resources.requests` y `limits` de CPU y memoria.
- [ ] `readinessProbe` y `livenessProbe`.
- [ ] `automountServiceAccountToken: false` si el pod no habla con la API de Kubernetes.
- [ ] Validado con `kubeconform` y `trivy config` en CI.

## Proceso
- [ ] El cambio entra por PR con revisión; nadie aplica a mano en producción.
- [ ] Hay plan de rollback probado (versión anterior de la imagen / `kubectl rollout undo`).
- [ ] Alertas y dashboards del servicio existen antes del primer despliegue.

> **Nota de la Semana 8:** `trivy fs --scanners secret` no detectó ni la contraseña dentro de
> `DATABASE_URL` ni la llave `sk_live_` de ejemplo, y `trivy config` ignoró el archivo
> `Dockerfile-inseguro` por su nombre. Los escáneres son una red de seguridad, no una revisión.
