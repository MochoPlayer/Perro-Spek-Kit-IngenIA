# Constitución de VOICE-BITTLE (reto Bittle, IngenIA Robótica 2026-2027)

Reglas fijas del proyecto. La IA (Spec Kit, Claude Code) las respeta en cada paso: `spec.md`,
`plan.md`, `tasks.md`, código y pruebas. Ninguna regla es nueva: cada una cita el sitio del
repositorio de donde sale. Copia para el hito H2: `H2-especificacion-planificacion/constitution.md`.

## Principios básicos

### I. Pruebas sin el robot físico (NO NEGOCIABLE)

- Todas las pruebas automáticas de H3 MUST ejecutarse completas sin el robot físico, sin
  micrófono y sin puerto serie, y MUST dar el mismo resultado cada vez.
- El robot se ve a través de una interfaz única con dos versiones: el enlace serie real y un
  robot simulado que registra los comandos. Las pruebas usan el robot simulado.
- Las pruebas con el robot físico, con voz real o con medidas de tiempo real son aparte (H4) y
  no sustituyen a las pruebas sin robot.

**Fuente**: `CLAUDE.md` («Las pruebas de H3 deben funcionar sin el robot físico»);
`H3-implementacion-pruebas/README.md` («pruebas reproducibles sin necesidad del robot físico»);
H1 CTX-08, NEC-08 y REQ-26 (`Entregable-H1.md` §2.3, §4.1, §5.4).

### II. No inventar contenido

- Cada dato (comando, valor numérico, decisión, respuesta del cliente) MUST salir de una fuente
  del repositorio: `referencias/`, la documentación de Petoi o las respuestas del cliente. El
  documento cita esa fuente.
- Si falta un dato, se anota como `OPEN-NN` (o como pendiente `P-NN` en `plan.md`) y se
  pregunta. No se rellena con un valor supuesto.
- Un valor numérico sin medir se marca `[provisional]` y va en un fichero de ajustes o de
  catálogo, no en el código.

**Fuente**: `CLAUDE.md` («No inventes contenido. Cada dato sale de una fuente del repo…»);
respuestas del cliente 26/10 y OPEN-02 (valores provisionales «a ojo» que se ajustan tras los
prototipos); `plan.md` (todos los valores provisionales van en `ajustes.json` o `catalogo.json`).

### III. No guardar audio ni datos personales

- El sistema MUST NOT guardar grabaciones de audio en el disco una vez transcrita la voz.
- Las pruebas automáticas entran por texto. El repositorio MUST NOT contener audios personales,
  credenciales ni claves de API.

**Fuente**: H1 REQ-24 (origen: cliente 26/10, punto 7, privacidad); `CLAUDE.md`
(«No subas credenciales, claves de API ni audios personales»).

### IV. La IA no decide por el equipo

- Los requisitos y los escenarios básicos los escribe el equipo. La IA MAY ampliarlos,
  corregirlos y cotejarlos, pero MUST NOT inventarlos desde cero ni reescribir los del equipo sin
  que se lo pidan.
- La arquitectura la define el equipo. Spec Kit la organiza; no la decide.
- Toda decisión que no esté fijada en H1, en `spec.md` o en una respuesta del cliente va como
  «propuesta, pendiente de confirmar por el equipo», con sus opciones. Las discrepancias y los
  pendientes se presentan con opciones y quedan abiertos hasta que el equipo responda.
- Spec Kit no trabaja solo: el equipo revisa cada salida antes de aceptarla.

**Fuente**: `CLAUDE.md` («Reglas del reto»: los requisitos los hace el equipo; Spec Kit no se
deja funcionar solo); `referencias/notas/sesion-2026-10-26.md` («nunca dejarlo funcionar solo,
genera mucha basura»); `H2-especificacion-planificacion/README.md` («definir vosotros la
arquitectura… No dejar que Spec Kit funcione solo»); `discrepancias.md` («la IA no decide por
el equipo»).

### V. Todo requisito se deriva a pruebas concretas

- Cada requisito (`REQ-NN`) MUST tener al menos una prueba concreta: qué se hace, qué se espera
  y en qué nivel (sin robot, voz real, robot físico o inspección).
- Los requisitos no funcionales MUST dar un valor concreto, sin palabras genéricas.
- Los requisitos de dominio (protocolos de seguridad, interfaz de frenado) no aplican en estas
  entregas.

**Fuente**: respuestas del cliente 26/10, punto 7 («Todo requisito debe ser derivable a pruebas
específicas»; «sin palabras grandes genéricas»; «de dominio no aplican»); `CLAUDE.md`.

### VI. Las respuestas del cliente mandan

- El profesor es el cliente. Su respuesta manda sobre cualquier suposición del equipo o de la
  IA. Si una respuesta cambia, gana la más reciente.
- La comunicación con el cliente va por Teams.

**Fuente**: `CLAUDE.md` («Reglas del reto» y «Hechos del cliente»);
`referencias/notas/respuestas-cliente-2026-10-26.md` (ajuste posterior: se pueden concatenar
órdenes).

### VII. Identificadores estables y trazabilidad

- Prefijos: `STK-NN`, `ESC-NN`, `NEC-NN`, `REQ-NN`, `OPEN-NN`, `CR-NN`. Los números existentes
  MUST NOT cambiar sin avisar.
- Si se renumera algo, se actualizan `Entregable-H1.md` §6 y §7 y todos los sitios donde
  aparece.
- Cada tarea de `tasks.md` cita los `REQ` que cubre y la decisión (`D-NN`) o el pendiente
  (`P-NN`) de `plan.md` de la que depende.

**Fuente**: `CLAUDE.md` («Identificadores»); `plan.md` («Lo que `tasks.md` debe respetar»).

### VIII. Todo en español

- Los documentos, los mensajes de commit, los avisos al usuario y los nombres del código del
  equipo se escriben en español.

**Fuente**: `CLAUDE.md` («Todo el repo está en español»; «Commits… con mensaje en español»).

## Restricciones del reto

- Robot: Petoi Bittle normal con placa NyBoard, sin módulo de voz (H1 CTX-01).
- Los ensayos con el robot físico se hacen sobre una superficie lisa y con una persona que vigile
  para evitar caídas (H1 REQ-28).
- Interfaz web o aplicación, a elección del equipo, probada en el ordenador propio (cliente
  26/10, punto 9).
- Para llamar al robot hay que decir su nombre, «Atenio» (cliente 26/10, punto 3; H1 REQ-01).
- Tiempo de respuesta: el mínimo posible (cliente 26/10, punto 4); el valor provisional está en
  REQ-21.

## Flujo de trabajo

- Orden de Spec Kit en H2: constitución → `spec.md` → clarify y revisión manual → arquitectura →
  `plan.md` → `tasks.md` → analyze (`CLAUDE.md`, «Spec Kit (H2)»).
- `spec.md` MUST recoger todos los escenarios, requisitos, casos excepcionales y criterios de
  aceptación de H1. Se comprueba la cobertura contra la trazabilidad antes de pasar a `plan.md`
  (`CLAUDE.md`).
- Se entrega el primer incremento identificado en `tasks.md` (`CLAUDE.md`).
- Commits pequeños, uno por cambio, en español y con el prefijo del hito: `H1: …`, `H2: …`
  (`CLAUDE.md`, «Convenciones»).
- Diagramas en Mermaid dentro del Markdown (`CLAUDE.md`, «Convenciones»).

## Gobierno

- Esta constitución resume reglas que ya están en `CLAUDE.md`, en el `README.md` y en H1. Si
  una de esas fuentes cambia, se cambia aquí en el mismo commit. Si las dos difieren, manda la
  fuente.
- Solo el equipo cambia esta constitución. Cada cambio sube la versión: MAYOR si se quita o se
  redefine un principio, MENOR si se añade uno, PARCHE si solo cambia la redacción.
- `plan.md` («Comprobación de la constitución») y el análisis de coherencia (`coherencia.md`)
  comprueban cada principio.
- `CLAUDE.md` es la guía de trabajo diaria para la IA.

**Versión**: 1.0.0 | **Ratificada**: 2026-11-04 | **Última modificación**: 2026-11-04
