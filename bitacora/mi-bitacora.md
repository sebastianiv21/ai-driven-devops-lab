# Bitácora de Colaboración con IA

> Asistí a las sesiones durante el programa (septiembre–noviembre de 2026) y consolidé los labs
> prácticos en la última semana: se ejecutaron y documentaron el 17 de noviembre de 2026. Cada
> entrada apunta a su evidencia en `bitacora/evidencia/semanaN/` (salidas reales de comandos,
> diffs, escaneos).
> Asistente usado en todo el curso: **Claude Code** (CLI, modo agente) sobre el repo local.
> Claude Code ejecutó los cambios en modo agente; yo definí el enfoque, revisé cada diff y validé
> con comandos reales.

---

## Encabezado del participante

**Nombre:** Luis Sebastián Ibarra Villamil
**Empresa / Rol (opcional):** Support Engineer en transición a DevOps; trabajo diario con EKS, Terraform y CI/CD
**Ruta elegida:** [x] A — Reto guiado (sandbox)   [ ] B — Problema propio
**Proyecto / Problema elegido:**
> Llevar `orders-api` de "funciona en mi laptop" a "listo para producción" usando la IA como
> copiloto en cada etapa: lógica de negocio, pipeline, IaC, automatización, incidente, runbook
> y hardening. Elegí la Ruta A para no exponer datos de mi empresa; donde aplica, conecto cada
> lab con lo que hago en el trabajo real.

**Stack utilizado:**
> Python 3.11/3.14 + Flask + pytest · Docker · GitHub Actions + actionlint · Terraform 1.9 +
> LocalStack 4.4 (todo en contenedores) · trivy (IaC, Dockerfile, k8s, secretos) · kubeconform ·
> Claude Code como asistente.

---

## Semana 1 — Fundamentos de IA para ingenieros (Diagnóstico inicial)

**¿Ya usas IA en tu trabajo, o es tu primer acercamiento?**
> [x] Ya la uso regularmente   [ ] La he probado poco   [ ] Es la primera vez

**¿Qué modelo(s) o herramienta(s) usas o has probado?**
> Claude Code (principal) y ChatGPT. En el trabajo uso Multica para orquestar agentes sobre issues
> de GitHub y Linear; en proyectos personales también uso Multica, con agentes Hermes y Pi.

**Si ya la usas: ¿para qué la has usado hasta ahora?**
> Investigar incidentes de clientes, escribir y revisar PRs de Terraform/Helm, depurar CI,
> triage de advisories de seguridad y documentación (runbooks).

**Si ya la usas: ¿sueles validar lo que te da, o normalmente lo tomas tal cual?**
> Valido casi siempre con `terraform plan`, tests o leyendo el diff. Mi punto débil: cuando no
> tengo contexto del área, tiendo a aceptar los defaults del agente más de lo que debería.

**Describe tu entorno de trabajo actual**
> AWS multi-región con EKS, Terraform con flujo de PR + apply desde CI, Argo CD, GitHub Actions,
> observabilidad con Grafana/Tempo/Loki. Soporte a clientes self-hosted (Docker/Kubernetes).

**¿Qué esperas lograr con este curso en tu día a día?**
> Pasar de "uso IA" a "uso IA con un proceso verificable": contexto estructurado, investigación
> antes del fix, y evidencia de cada decisión.

Evidencia: `evidencia/semana1/health-check.txt` — la app corre (`{"status":"ok"}`), y el endpoint
de cotización ya mostraba el bug de la Semana 2 (10 artículos → `90.0`).

---

## Semana 2 — Desarrollo asistido por IA / Testing y calidad con IA

**¿Usaste IA para acelerar programación, debugging, documentación o revisión de código esta semana? ¿O para generar/mejorar casos de prueba?**
> Sí: para investigar el bug de descuento y para proponer casos límite que los tests no cubrían.

**Contexto que le diste a la IA**
> La regla de negocio completa (6–9 → 10 %, ≥10 → 15 %, <6 → 0 %), `app/api/orders.py`, el
> test que fallaba y la instrucción de explicar la causa **antes** de proponer el fix.

**Problema o pregunta que trabajaste**
> Clientes con exactamente 10 artículos reciben 10 % en vez de 15 %.

**Cómo usaste la IA**
> 1) Corrí los tests antes de mirar el código: 1 falla (`assert 90.0 == 85.0`).
> 2) La IA identificó que `total_quantity > 10` excluye el 10 y que la regla dice "10 o más".
> 3) Le pedí casos límite adicionales; propuso 5, 9, orden vacía y **varias líneas que suman 10**.
> 4) Escribí esos tests primero: el de varias líneas también falló, confirmando que el bug no
>    era solo del caso de una línea. Luego apliqué el fix (`>= 10`, y `>= 6` por legibilidad).

**Cómo validaste lo que propuso**
> Los tests nuevos fallaron antes del fix (2 fallas) y pasaron después (8/8). También verifiqué
> el endpoint real: 10 artículos → `85.0` (ver Semana 8, contenedor endurecido).
> Evidencia: `evidencia/semana2/01..04`.

**Qué acertó / qué falló la IA**
> Acertó la causa a la primera. Su aporte más valioso fue el caso de varias líneas: es el que un
> cliente real dispara y no estaba cubierto. No falló en este lab.

**Habilidad practicada esta semana**
> [x] Contexto estructurado a la IA   [x] Investigación antes de solución   [x] Validación de comandos/config   [ ] Protección de información sensible

**Lección aprendida (una frase)**
> Un test que falla antes del fix vale más que la explicación de la IA: es la prueba de que la hipótesis era la correcta.

---

