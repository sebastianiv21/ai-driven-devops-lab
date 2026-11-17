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
> Evidencia: `evidencia/semana2/01..04`. En GitHub Actions: el CI falló con el bug
> ([corrida roja](https://github.com/sebastianiv21/ai-driven-devops-lab/actions/runs/44151930359),
> `assert 90.0 == 85.0`) y pasó con el fix
> ([corrida verde](https://github.com/sebastianiv21/ai-driven-devops-lab/actions/runs/44152517650)).

**Qué acertó / qué falló la IA**
> Acertó la causa a la primera. Su aporte más valioso fue el caso de varias líneas: es el que un
> cliente real dispara y no estaba cubierto. No falló en este lab.

**Habilidad practicada esta semana**
> [x] Contexto estructurado a la IA   [x] Investigación antes de solución   [x] Validación de comandos/config   [ ] Protección de información sensible

**Lección aprendida (una frase)**
> Un test que falla antes del fix vale más que la explicación de la IA: es la prueba de que la hipótesis era la correcta.

---

## Semana 3 — Fundamentos de CI/CD / Pipelines con IA

**¿Analizaste, troubleshooteaste o mejoraste un pipeline (propio o del sandbox) con ayuda de IA esta semana?**
> Sí, el pipeline del sandbox.

**Contexto que le diste a la IA**
> `pipeline-con-bug.yml`, el `ci.yml` de referencia, y la instrucción de predecir el error antes de correrlo.

**Problema o pregunta que trabajaste**
> El pipeline falla en cada push después de "solo reordenar pasos".

**Cómo usaste la IA**
> Predicción de la IA: con el paso de tests antes de la instalación, `setup-python` deja un
> Python limpio y el paso falla con `No module named pytest`. Para confirmarlo sin GitHub,
> reproduje ambos órdenes en un contenedor limpio `python:3.11-slim` (misma versión que el
> workflow). Después le pedí una mejora adicional.

**Cómo validaste lo que propuso**
> - Orden con bug: `/usr/local/bin/python: No module named pytest`, exit 1 → coincide con la predicción.
> - Orden corregido: 8 passed, exit 0.
> - Mejoras aplicadas a `.github/workflows/ci.yml`: caché de pip (`cache: pip` +
>   `cache-dependency-path`, sintaxis verificada en la documentación de `actions/setup-python@v5`)
>   y `permissions: contents: read` (mínimo privilegio para el `GITHUB_TOKEN`).
> - `actionlint` sobre ambos workflows: 0 errores.
> Evidencia: `evidencia/semana3/01..03` y la
> [corrida del CI endurecido en GitHub](https://github.com/sebastianiv21/ai-driven-devops-lab/actions/runs/44153834624).

**Qué acertó / qué falló la IA**
> Acertó la predicción exacta. Falló en un detalle de herramienta: usó `actionlint -color=never`,
> un flag que no existe (`-color` es booleano; el correcto es `-no-color`). Lo detecté porque el
> comando devolvió el texto de ayuda en vez de un resultado.

**Habilidad practicada esta semana**
> [x] Contexto estructurado a la IA   [x] Investigación antes de solución   [x] Validación de comandos/config   [ ] Protección de información sensible

**Lección aprendida (una frase)**
> Pedirle a la IA que prediga el fallo y luego reproducirlo convierte una suposición en evidencia; y los flags de CLI que "suenan bien" se verifican igual.

---

## Semana 4 — Arquitecturas modernas con IA / Servicios de IA en la nube

**¿Usaste IA para razonar sobre una decisión de arquitectura, o evaluaste/integraste algún servicio de IA gestionado esta semana?**
> Sí: revisión de seguridad del bucket S3 y diseño conceptual de búsqueda semántica sobre los reportes.

**Contexto que le diste a la IA**
> `main.tf` completo, que el bucket guardará reportes con datos de clientes, y la pregunta:
> "¿esta configuración es apropiada para datos de clientes? Explica antes de corregir".

**Problema o pregunta que trabajaste**
> Bucket con `acl = "public-read"` y versionado `Disabled`, pendiente de aprobar.

**Cómo usaste la IA**
> 1) Explicación línea por línea: `public-read` deja listar y descargar todos los reportes de
>    forma anónima; sin versionado, un borrado o sobrescritura no se puede recuperar.
> 2) `terraform plan` contra LocalStack (Terraform y LocalStack en Docker; nunca `apply`).
>    **El plan pasó sin advertencias**: Terraform no evalúa si algo es seguro.
> 3) `trivy config` sobre el original: 9 hallazgos (6 HIGH), entre ellos el ACL público y la
>    ausencia de public access block, cifrado con llave propia y versionado.
> 4) Corregí: `BucketOwnerEnforced` (ACLs desactivadas), public access block completo, cifrado
>    SSE-KMS con llave propia y rotación, versionado `Enabled`, lifecycle que expira versiones
>    viejas a los 90 días (controla el costo del versionado) y policy que rechaza tráfico sin TLS.

**Cómo validaste lo que propuso**
> `terraform validate` OK; `plan`: 8 recursos a crear; `trivy config` del corregido: **0 hallazgos**.
> Excepción documentada en el código: logging de acceso (AWS-0089, LOW), que requiere un bucket
> de logs dedicado fuera del alcance del lab.
> Evidencia: `evidencia/semana4/01..04` y `main.tf.original`.

**Qué acertó / qué falló la IA**
> Además de los dos riesgos evidentes (ACL pública y versionado), propuso controles que el lab no
> pedía: lifecycle para el costo del versionado y la policy de solo-TLS. El escáner aportó lo que
> la revisión inicial no mencionó: cifrado con llave administrada por el equipo.

**Parte 2 — Servicio de IA en la nube (diseño, sin implementar)**
> Búsqueda semántica sobre los reportes: **Amazon Bedrock Knowledge Bases** apuntando a este
> mismo bucket como fuente (chunking, embeddings con Titan y vector store gestionados; se
> resincroniza cuando el worker escribe reportes nuevos). Alternativa si ya existe Postgres:
> `pgvector` con embeddings generados por un job, menos piezas gestionadas pero más código propio.
> Consideraciones: los reportes tienen datos de clientes → redactar PII antes de generar
> embeddings, mismo KMS, rol IAM de solo lectura sobre el bucket, región que cumpla la residencia
> de datos, y costo por sincronización. Esto no se puede validar con LocalStack: se probaría en
> una cuenta sandbox con datos sintéticos.

**Habilidad practicada esta semana**
> [x] Contexto estructurado a la IA   [x] Investigación antes de solución   [x] Validación de comandos/config   [x] Protección de información sensible

**Lección aprendida (una frase)**
> Un `terraform plan` limpio solo dice que el código es válido, no que sea seguro: la revisión de seguridad es un paso aparte.

---

## Semana 5 — Introducción a agentes / Desarrollo de agentes

**¿Construiste, configuraste o probaste un agente de IA aplicado a tu problema esta semana?**
> Sí: completé el agente de reintentos de órdenes fallidas.

**Contexto que le diste a la IA**
> El esqueleto con TODOs, la cola de ejemplo y mis decisiones de diseño como requisitos: no
> reintentar más allá de `MAX_RETRIES`, escalar a un humano, y no actuar en masa.

**Problema o pregunta que trabajaste**
> Automatizar el reintento de órdenes fallidas sin crear un agente que empeore un incidente.

**Cómo usaste la IA**
> Primero escribí los tests que fijan cada decisión (9 tests, todos fallando antes de
> implementar), luego la implementación. Decisiones:
> - Cola inexistente → lista vacía (no es error); JSON corrupto → falla ruidosamente (no sobrescribir lo que no entiende).
> - `failed` con intentos < 3 → se re-encola como `pending` (+1 intento); el agente no procesa, solo re-encola.
> - `failed` con 3 intentos → `needs_human`, nunca más reintentos.
> - Circuit breaker: más de 20 fallas a la vez = problema sistémico → no toca nada y alerta.
> - `--dry-run`, escritura atómica de la cola, log con timestamp de cada acción.

**Cómo validaste lo que propuso**
> 15/15 tests pasan: los 9 iniciales más 6 agregados tras revisión (límite exacto del circuit
> breaker en 20, `attempts=2`, orden sin campo `attempts`, sin acciones no reescribe la cola,
> código de salida 2 cuando se aborta, y la cola reescrita conserva permisos 0644 sin dejar
> `.tmp` huérfanos; este último falló antes del fix porque el archivo temporal se crea con 0600). CI corre ahora también estos tests.
> Corrida real sobre `app/worker/queue.json`: ORD-1002 re-encolada (intento
> 2/3), ORD-1003 escalada, ORD-1001/1004 sin cambios; segunda corrida no hace nada (idempotente).
> Evidencia: `evidencia/semana5/01..03`.

**Qué acertó / qué falló la IA**
> La implementación salió bien a la primera porque los tests definían el comportamiento. El
> hallazgo importante vino de **verificar más allá del agente**: al correr el worker después, procesa
> las 4 órdenes, incluidas `completed` y `needs_human`. El worker ignora el `status`, así que la
> escalación no tiene efecto aguas abajo. Lo dejo documentado como riesgo; arreglarlo es cambiar
> el worker, fuera del alcance del lab. Segundo riesgo conocido: la escritura de la cola es
> atómica pero sin lock, así que si el worker escribe al mismo tiempo una de las dos escrituras
> se pierde; en producción la cola debería vivir en un sistema con concurrencia (SQS, una tabla).
> Tras la revisión, el agente sale con código 2 cuando se activa el circuit breaker, para que
> cron/CI lo trate como alerta y no como corrida exitosa.

**Habilidad practicada esta semana**
> [x] Contexto estructurado a la IA   [x] Investigación antes de solución   [x] Validación de comandos/config   [ ] Protección de información sensible

**Lección aprendida (una frase)**
> La autonomía de un agente se diseña por sus límites (cuándo se detiene, cuándo escala), y hay que probar el sistema completo, no solo el agente.

---

