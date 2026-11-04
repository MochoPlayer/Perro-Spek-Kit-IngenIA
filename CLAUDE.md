# CLAUDE.md

Repo del reto **Bittle** de IngenIA Robótica (curso 2026-2027): el robot Petoi Bittle debe obedecer órdenes de voz.
Todo el repo está en español. Responde en español y escribe los documentos en español.

Lee primero `README.md` (hitos, itinerario, flujo de trabajo y reglas). Este archivo solo dice dónde está cada cosa y cómo ahorrar trabajo.

## Reglas del reto (no las rompas)

- **Los requisitos y escenarios básicos los hace el equipo, no la IA.** La IA puede ampliarlos, corregirlos y cotejarlos. No los inventes desde cero ni reescribas los del equipo sin que se lo pidan.
- **Spec Kit no se deja funcionar solo**: genera mucha basura. Revisa cada salida con el equipo.
- No inventes contenido. Cada dato sale de una fuente del repo (`referencias/`, documentación de Petoi, respuestas del cliente). Si falta un dato, anótalo como `OPEN-NN` y pregunta.
- El profesor es el **cliente**. Las respuestas del cliente mandan sobre cualquier suposición; si una respuesta cambia, gana la más reciente (ver `referencias/notas/respuestas-cliente-2026-10-26.md`).
- Todo requisito debe poder derivarse a pruebas concretas. Los requisitos de dominio (seguridad, frenado) no aplican en estas entregas.
- Las pruebas de H3 deben funcionar **sin el robot físico**.

## Carpetas

| Carpeta | Qué hay | Hito |
|---|---|---|
| `H1-especificacion-inicial/` | Investigación, órdenes, escenarios, necesidades, requisitos y trazabilidad. Entrega por Moodle. | H1 |
| `H2-especificacion-planificacion/` | `constitution`, `spec.md`, arquitectura, `plan.md`, `tasks.md`, coherencia. Se entrega el enlace al repo. | H2 |
| `H3-implementacion-pruebas/` | Casos de prueba, `src/`, `tests/`, revisión de código. | H3 |
| `H4-demostracion-aceptacion/` | Análisis de CR-01, ensayos físicos, `evidencias/`, presentación. | H4 |
| `referencias/` | Enlaces a fuentes y notas de las sesiones (transcripciones y resúmenes). | todos |

H2, H3 y H4 solo tienen su `README.md` por ahora. Cada `README.md` de hito trae el objetivo, el mínimo exigido y el flujo de trabajo con casillas.

### Dentro de `H1-especificacion-inicial/`

| Archivo | Para qué sirve |
|---|---|
| `Entregable-H1.md` | **Documento principal de H1** (el que se entrega, ~50 KB). Sigue la plantilla de la asignatura. |
| `entregables/PLANTILLA_H1_….docx` | Plantilla oficial opcional en Word. |
| `capacidades-bittle.md` | Investigación técnica del robot: vías de control, skills, articulaciones, tokens, secuencias. |
| `comandos-bittle-estandar-seguros.md` | Catálogo de los 45 comandos seguros del Bittle estándar. |
| `ordenes-modulo-voz-petoi.md` | Las 40 órdenes oficiales del módulo de voz de Petoi, con su comando. |
| `opciones-ordenes-de-voz.md` | Órdenes candidatas en tres tiers. |
| `propuesta-requisitos-funcionales-por-tiers.md` | Versión limpia de los tiers para enseñar al cliente. |
| `preguntas-para-el-cliente.md` | Preguntas para el profesor y datos que faltan. |

## Identificadores

Usa estos prefijos y no cambies los números existentes sin avisar (la trazabilidad depende de ellos):

`STK-NN` stakeholder · `ESC-NN` escenario · `NEC-NN` necesidad · `REQ-NN` requisito · `OPEN-NN` duda abierta · `CR-NN` solicitud de cambio.

Si renumeras algo (por ejemplo ESC-11 → ESC-10), actualiza `Entregable-H1.md` §6 y §7 y los demás sitios donde aparezca (`grep -r "ESC-11"`).

## Referencias y notas de sesión (para ir más rápido)

Antes de preguntar al equipo o releer una grabación, mira aquí. Los resúmenes ya contienen lo importante.

| Archivo | Qué es | Cuándo leerlo |
|---|---|---|
| `referencias/enlaces.md` | Todas las fuentes de la presentación *Semana 7 – Bittle*, por tema e hito: Petoi, SEBoK, Sommerville, NASA, Spec Kit. | Al citar una fuente o buscar dónde se explica algo. |
| `referencias/notas/sesion-2026-10-26.md` | **Resumen** de la sesión del 26/10: enfoque del reto, entregables, rol de cliente, próximos pasos, decisiones. | Primera lectura para entender el contexto. |
| `referencias/notas/respuestas-cliente-2026-10-26.md` | **Respuestas del cliente** a las 10 preguntas, tal cual. Incluye el ajuste posterior (se pueden concatenar órdenes). | Antes de escribir o cambiar cualquier requisito. |
| `referencias/notas/transcripcion-2026-10-26.md` | Transcripción literal de la sesión (Wispr Flow). | Solo para comprobar una frase exacta del profesor. Es larga. |
| `referencias/notas/transcripcion-aclaracion-preguntas-2026-10-26.md` | Transcripción literal de la reunión de aclaración con el cliente. | Solo para comprobar una respuesta del cliente. Es larga. |

Hechos del cliente que ya están resumidos (no los vuelvas a preguntar):

- El cliente conoce los comandos que reconoce el robot.
- Para llamar al robot hay que decir su **nombre**; la voz interpreta todo lo demás.
- Tiempo de respuesta: **el mínimo posible**.
- 40 órdenes programadas (las del módulo de voz de Petoi); añadir más es positivo.
- Si la voz no se entiende, el ordenador puede responder "no se ha entendido bien".
- Interfaz: web o aplicación, a elección del equipo, probada en el ordenador propio.
- Requisitos: funcionales, no funcionales (concretos, sin palabras genéricas) y de dominio (no aplican).
- Spec Kit es un módulo que conecta con ChatGPT o Claude Code y ayuda a traducir requisitos a spec/plan/tasks.
- Comunicación con el cliente: **Teams**.

### Al añadir una sesión nueva

1. Guarda la transcripción tal cual (sin corregir) en `referencias/notas/transcripcion-AAAA-MM-DD.md`, con la fuente en la cabecera.
2. Escribe el resumen en `referencias/notas/sesion-AAAA-MM-DD.md` (enfoque, entregables, próximos pasos, decisiones).
3. Si el cliente respondió dudas, crea `respuestas-cliente-AAAA-MM-DD.md` con sus palabras exactas, sin interpretar.
4. Añade la entrada en `referencias/enlaces.md` (sección *Notas de las sesiones*) y en la tabla de arriba.
5. Si algo cambia un requisito, actualiza `H1-especificacion-inicial/` y cierra o abre los `OPEN-NN` que toquen.

## Spec Kit (H2)

- Documentación: `referencias/enlaces.md`, sección *Spec Kit y repositorio*.
- Orden de trabajo: constitución → `spec.md` → clarify y revisión manual → arquitectura → `plan.md` → `tasks.md` → analyze.
- `spec.md` debe recoger todos los escenarios, requisitos, casos excepcionales y criterios de aceptación de H1. Comprueba la cobertura contra la trazabilidad antes de pasar a `plan.md`.
- Entrega el primer incremento identificado en `tasks.md`.

### Próximo paso: resolver las discrepancias de H2

`spec.md`, `plan.md` y `tasks.md` están escritos, pero H2 no se entrega hasta resolver las 15 discrepancias de `H2-especificacion-planificacion/discrepancias.md`. **Cuando se retome IngenIA, empieza por ese archivo**: lee su sección «Cómo retomar el trabajo», pregunta al equipo las filas sin respuesta y aplica las respuestas. No decidas por el equipo.

## Convenciones

- Diagramas en Mermaid dentro del Markdown (ver el flujo del `README.md`).
- Commits pequeños, uno por cambio, con mensaje en español y prefijo del hito: `H1: …`, `H2: …`.
- No subas credenciales, claves de API ni audios personales.
