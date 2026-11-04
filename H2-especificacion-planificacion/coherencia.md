# H2 · Análisis de coherencia (`/speckit-analyze`)

**Fecha**: 2026-11-04 · **Documentos analizados**: [`spec.md`](spec.md), [`plan.md`](plan.md) (`c9d583c`), [`tasks.md`](tasks.md) (`461b7d5`), [`constitution.md`](constitution.md) v1.0.0, H1 (`Entregable-H1.md`) y el código de `H3-implementacion-pruebas/` (263 pruebas, todas pasan).

> **Cómo leer este informe.** Es el paso «Analyze» del flujo de H2 (`README.md`). Spec Kit lo genera en modo solo lectura: este informe no cambia `spec.md`, `plan.md` ni `tasks.md`. Las recomendaciones son propuestas. **El equipo decide** (constitución, principio IV). Las 13 discrepancias abiertas de [`discrepancias.md`](discrepancias.md) y los pendientes P-01 a P-10 de `plan.md` no se repiten aquí: se citan por su ID y siguen como «pendiente del equipo».
>
> Gravedad: **CRÍTICA** (incumple la constitución o deja sin cubrir lo mínimo del reto), **ALTA** (requisitos en conflicto, criterio que no se puede probar), **MEDIA** (falta cobertura o un caso está poco definido), **BAJA** (redacción, duplicados sin efecto).

## Resultado

- **Ningún hallazgo CRÍTICO.** Ninguna parte de spec, plan o tareas incumple un principio de la constitución.
- **Cobertura**: los 35 REQ y los 12 SC tienen al menos una tarea (100 %). 30 REQ tienen código y pruebas sin robot en H3.
- **Lo que impide entregar H2** no es una contradicción nueva: son las 13 discrepancias abiertas y los pendientes P-NN, que el equipo debe decidir.

## Hallazgos

| ID | Categoría | Gravedad | Dónde | Qué pasa | Recomendación (propuesta) |
|----|-----------|----------|-------|----------|---------------------------|
| C1 | Cobertura | ALTA | `spec.md` SC-001; `tasks.md` T074; `plan.md` P-01, P-02, P-06, P-07 | El criterio mínimo del reto (SC-001: dos órdenes válidas y una entrada no reconocida, con voz y robot) depende de cuatro pendientes sin decidir. Ninguna tarea de voz real (fase 10) ni de interfaz (fase 11) ha empezado. | Decidir P-01 (motor de voz) y P-06 (interfaz) pronto. Hacer el prototipo T047 antes que el resto del segundo incremento. |
| C2 | Inconsistencia | ALTA | `plan.md` P-07; `tasks.md` T057, T058 | «Otro ordenador» (P-07) puede cambiar la arquitectura (habría que añadir una interfaz de red entre componentes). Todo el plan supone un solo portátil (CTX-01). | Preguntar al cliente por Teams qué quiso decir, antes de empezar la fase 11. |
| U1 | Poco definido | MEDIA | `spec.md` REQ-12, REQ-13 | No hay regla escrita para separar «sin sentido» de «fuera del catálogo» ni para el ruido sin «Atenio». Las pruebas usan la opción 1 de Y-02 de forma provisional (marca `discrepancia("Y-02")`). | Ver Y-02 y Y-04 de `discrepancias.md`. |
| U2 | Poco definido | MEDIA | `spec.md` REQ-19; `tasks.md` T060; `gestor_acciones.py` | REQ-19 pide mostrar el estado de la conexión. El gestor solo publica un evento de estado de conexión cuando la pierde, no al conectar ni al arrancar. | Al hacer T060 y T056, publicar el estado también al conectar. |
| U3 | Poco definido | MEDIA | `spec.md` REQ-21, SC-004; `tasks.md` T020 | La parte de software de la latencia solo se comprueba con el reloj simulado (el comando sale en el instante 0). No hay 20 mediciones con reloj real (T020 sin empezar). | Hacer T020. La medida completa espera a P-01 (T052). |
| U4 | Poco definido | MEDIA | `spec.md` REQ-24, SC-008; `tasks.md` T049 | REQ-24 (no guardar audio) no tiene ninguna prueba todavía, porque no existe la captura de audio. | Hacer T049 con un motor falso en cuanto se empiece la fase 10. |
| D1 | Constitución (IV) | MEDIA | `tasks.md` T001; `plan.md` P-10 | El código de H3 se construyó con las propuestas D-01, D-05, D-08 y D-09 (lenguaje, catálogo en fichero, reloj, pruebas por texto), pero el equipo no ha confirmado P-10. `tasks.md` lo permite («se puede empezar con el valor propuesto»), pero la tarea que abre todo sigue abierta. | El equipo confirma o cambia P-10 y lo anota en `plan.md`. |
| D2 | Constitución (IV) | MEDIA | `datos/catalogo.json` (`_descripcion`); `tests/frases/`; `tasks.md` T010, T011 | Los sinónimos del catálogo salen de `opciones-ordenes-de-voz.md`, pero están «pendientes de aprobar por el equipo». T011 pide que el equipo escriba o revise las frases de prueba. | El equipo revisa los sinónimos y las frases y lo anota en T010 y T011. |
| D3 | Constitución (I) | MEDIA | `tasks.md` T012, T026; `tests/conftest.py` | Hoy ninguna prueba abre un puerto real ni el micrófono, pero no hay guardián que lo impida (T012) ni prueba que lo compruebe (T026). | Hacer T012 y T026. |
| D4 | Constitución (II) | BAJA | `datos/ajustes.json` (`fin_de_linea`) | El campo `fuente` dice «No consta en `capacidades-bittle.md`». H1 §2.4 sí lo dice: «carácter token + argumentos + salto de línea» y «`ksit\n`» (`Entregable-H1.md`, fila «Protocolo de comunicación serie»). | Cambiar la fuente a H1 §2.4. El valor sigue por confirmar en la sesión 2 (I-4). |
| D5 | Constitución (II) | BAJA | `eventos.py`, `interprete.py` | `spec.md` no fija el texto exacto de tres avisos: orden no disponible (REQ-13), batería baja (REQ-33) y pérdida de conexión (D-13). El código usa textos propios, marcados en comentarios como no fijados. | El equipo confirma los textos o los escribe en `spec.md`. |
| I1 | Inconsistencia | BAJA | `tasks.md` T005, T031; `interprete.py` | Las tareas ponen las palabras de enlace en `ajustes.json`. El código las tiene como parámetro de `Interprete` (valor inicial «y», «luego»), no en `ajustes.json`. | Al cerrar P-03, decidir dónde van y alinear tarea y código. |
| I2 | Inconsistencia | BAJA | `tasks.md` T008, T009, T013 a T015, T021, T028 y otras | Las tareas proponen un fichero de prueba por tema (`test_interprete_activacion.py`…). El código agrupa las pruebas en menos ficheros. `tasks.md` ya explica la equivalencia («Estado al 04/11»). | Ninguna, salvo que el equipo prefiera los nombres de las tareas. |
| I3 | Inconsistencia | BAJA | `src/atenio/`; `plan.md` «Esquema del sistema» | El esquema dice que el intérprete envía el texto a la interfaz. En el código nadie publica el evento «texto reconocido»: lo hace la clase de prueba `Cadena`. | Asignarlo a `principal.py` o al adaptador de transcripción (T019, T057). |
| A1 | Duplicado | BAJA | `plan.md` y `tasks.md` «Discrepancias detectadas»; `discrepancias.md` | Las discrepancias están en tres sitios. `discrepancias.md` dice que manda él. | Dejar en `plan.md` y `tasks.md` solo un enlace a `discrepancias.md` cuando se resuelvan. |
| A2 | Ambigüedad | BAJA | `spec.md` Casos límite («Ruido durante la demostración»); `plan.md` R-07 | «Ruido alto» no tiene medida. El riesgo está aceptado y REQ-22 se mide en sala tranquila. | Ninguna mientras el riesgo siga aceptado. |

**Discrepancias y pendientes que siguen abiertos** (pendientes del equipo, con sus opciones en `discrepancias.md` y `plan.md`):

| Afecta a | Abiertos |
|---|---|
| Qué hace el sistema | Y-02, Y-04, Y-03, X-06, X-07 |
| H1 frente a otras fuentes | X-01, X-02, X-03, X-04, X-05 |
| Faltan cosas en H2 | Y-01, Y-05, Y-06 |
| Decisiones técnicas | P-01 a P-10 |

## Cobertura de requisitos

Tareas: trazabilidad REQ → tareas de `tasks.md`. Estado de las pruebas: [`H3-implementacion-pruebas/plan-pruebas.md`](../H3-implementacion-pruebas/plan-pruebas.md).

| REQ | ¿Tiene tarea? | Tareas principales | Nota |
|---|---|---|---|
| REQ-01 | Sí | T013, T016, T022 | Pruebas sin robot en verde. Falta voz real (OPEN-01). |
| REQ-02 a REQ-06, REQ-08, REQ-10 | Sí | T010, T015, T016, T018 | Pruebas sin robot en verde. Faltan duraciones (P-03) y robot físico. |
| REQ-07 | Sí | T034, T035, T037, T038 | En verde; la cola tras «para» depende de P-04. |
| REQ-09, REQ-11 | Sí | T010, T015, T071 | En verde; comando por confirmar en el robot (OPEN-03). |
| REQ-12, REQ-13 | Sí | T021, T022, T024 | En verde con la opción provisional de Y-02. |
| REQ-14 a REQ-16 | Sí | T066, T067, T080 | Solo catálogo; espera a P-09. |
| REQ-17, REQ-22 | Sí | T051, T053 | Sin código; espera a P-01. |
| REQ-18 | Sí | T013, T016, T050 | Intérprete en verde; transcripción espera a P-01. |
| REQ-19 | Sí | T009, T055, T056 | Eventos en código; interfaz espera a P-06. Ver U2. |
| REQ-20 | Sí | T008, T015, T043, T044 | En verde sin robot; puerto y baudios esperan a P-02. |
| REQ-21 | Sí | T020, T052 | Ver U3. |
| REQ-23 | Sí | T023, T025 | En verde. |
| REQ-24 | Sí | T049, T054 | Sin prueba todavía. Ver U4. |
| REQ-25 | Sí | T059, T060, T061 | En verde; pérdida durante una acción depende de P-08. |
| REQ-26 | Sí | T026, T027, T041 | Todo el conjunto pasa sin robot; faltan T026 y T027. |
| REQ-27 | Sí | T057, T058 | Sin código; espera a P-07. |
| REQ-28 | Sí | T068 | Procedimiento, inspección. |
| REQ-29, REQ-32 | Sí | T028 a T033 | En verde con duraciones de prueba; depende de P-03. |
| REQ-30 | Sí | T036, T039, T040 | En verde con `d` provisional; depende de P-05 y Y-03. |
| REQ-31 | Sí | T062, T063 | En verde; comando depende de P-05. |
| REQ-33 | Sí | T064 | En verde. |
| REQ-34 | Sí | T065, T079 | En verde (no se envía `G`/`g`); D-12 sin confirmar (Y-01). |
| REQ-35 | Sí | T014, T017 | En verde. |

| SC | ¿Tiene tarea? | Tareas | Nota |
|---|---|---|---|
| SC-001 | Sí | T074 | Ver C1. |
| SC-002, SC-005, SC-006, SC-009 a SC-012 | Sí | T015, T022, T023, T030, T029, T036, T034 | Pruebas sin robot en verde (algunas con marca de pendiente). |
| SC-003, SC-004, SC-008 | Sí | T053, T052, T054 | Esperan a P-01. |
| SC-007 | Sí | T027, T041 | El conjunto pasa sin robot; falta el script que lo ejecuta dos veces. |

**Tareas sin requisito**: ninguna. Todas citan al menos un REQ, salvo T001 (decisión P-10, base de todas) y T084 (este análisis, «todos»).

## Métricas

- Requisitos: 35 REQ (H1 y `spec.md`, los mismos) y 12 SC.
- Tareas: 84 (T001 a T084). Hechas: 19. Código hecho, sin cerrar: 26. Sin empezar: 39.
- Cobertura (requisitos con al menos una tarea): 100 %.
- Ambigüedades: 5 (U1 a U4, A2).
- Duplicados: 1 (A1).
- Hallazgos CRÍTICOS: 0.

## Siguientes pasos (propuesta)

No hay hallazgos críticos: se puede seguir con H3 sin `/speckit-implement`. Antes de entregar H2:

1. El equipo responde las 13 discrepancias de `discrepancias.md` (primero las de la sección A: Y-02, Y-04, Y-03, X-06, X-07).
2. El equipo decide P-10 (D1) y revisa sinónimos y frases (D2).
3. Preguntar al cliente por Teams sobre P-07 (C2).
4. Correcciones pequeñas que no cambian requisitos: D4, I1 (al cerrar P-03), I3.
5. Volver a ejecutar `/speckit-analyze` cuando se apliquen las respuestas y actualizar este informe.
