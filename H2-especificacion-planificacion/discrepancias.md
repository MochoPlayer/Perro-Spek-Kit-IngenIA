# H2 · Discrepancias por resolver

**Estado**: 1 de 15 resueltas (X-08) · **Fecha**: 2026-10-26, actualizado 2026-11-04 · **Documentos revisados**: `spec.md`, `plan.md` (`7b92170`), `tasks.md` (`c5e518b`) y H1.

## Cómo retomar el trabajo

Este es el **siguiente paso de H2**. Antes de entregar hay que resolver las 15 discrepancias de abajo.

1. El equipo escribe su decisión en la columna «Respuesta del equipo» (las dudas para el profesor van por Teams).
2. Quien trabaje con la IA le pide: «resuelve las discrepancias de `discrepancias.md` con las respuestas del equipo».
3. Se corrigen `spec.md`, `plan.md`, `tasks.md` y H1 según las respuestas, un commit por discrepancia (`H2: …`). Se pasa cada fila a «Resuelta» y se actualiza el contador de arriba.
4. Se escribe `constitution.md` y `arquitectura.md` si el equipo lo decide (ver X-08), se ejecuta el análisis de coherencia (`coherencia.md`), se etiqueta H2 en Git y se entrega el enlace al repositorio.

Reglas: la IA no decide por el equipo. Las opciones son propuestas. Si una respuesta cambia un requisito, se actualizan los IDs y la trazabilidad (`grep -r "REQ-NN"`). Una respuesta del cliente siempre manda sobre una suposición.

**Aparte** están las decisiones técnicas P-01 a P-10 de `plan.md` (motor de voz, USB o Bluetooth, duraciones, etc.): no son contradicciones y no están en esta lista. Bloquean 33 tareas de `tasks.md`.

Hay una copia editable de esta lista en Claude Docs: <https://claude.ai/artifact/Xh5yXVsnHqrbi38uJmQsix> (privada, la abre quien la tenga compartida). Si las dos difieren, manda este archivo.

## A. Cambian lo que hace el sistema (decidir primero)

| ID | Qué pasa | Opciones | Respuesta del equipo |
| --- | --- | --- | --- |
| Z-01 | **Palabra de activación.** Mario pide «Perro» en lugar de «Atenio» (04/11). El código ya usa el ajuste `palabra_activacion` de `H3-implementacion-pruebas/datos/ajustes.json` (valor «perro»). | Falta: confirmar en equipo y cambiar REQ-01, REQ-35, decisión 055 y los textos de H1/spec. | |
| Y-02 | **Aviso por ruido o ignorar.** REQ-12 pide el aviso «no se ha entendido bien» ante ruido o frases sin sentido. El contrato del intérprete dice que sin «Atenio» no se hace nada ni se avisa (REQ-01). El ruido sin «Atenio» cae en las dos reglas. Tampoco hay criterio para separar «sin sentido» (REQ-12) de «orden fuera del catálogo» (REQ-13). Afecta a T021, T022 y T024. | 1) Sin «Atenio» se ignora todo, ruido incluido; el aviso solo sale cuando hay «Atenio». 2) Aviso también ante ruido sin «Atenio». Además hay que escribir la regla que separa «sin sentido» de «fuera del catálogo». | |
| Y-04 | **«Ningún comando de movimiento» o «ningún comando».** REQ-12 dice «de movimiento»; REQ-13 dice «ningún comando». Las pruebas (T022) comprueban que no sale ningún comando en los dos casos. | 1) Cambiar REQ-12 a «ningún comando». 2) Dejarlo y listar qué comandos que no son de movimiento se permiten. | |
| Y-03 | **Parada de emergencia y «reposo».** REQ-30 dice «modo reposo». D-11 propone `d` para la parada. En REQ-08 `d` es «tumbarse y apagar los motores», no reposo (`krest`). | 1) Parada con `d` y cambiar la redacción de REQ-30 (o la de REQ-08). 2) Parada con `krest`. Se prueba en la sesión 2 con el robot (OPEN-11, P-05). | |
| X-06 | **Qué hace el robot ante una entrada no reconocida.** El objetivo 4 de H1 §2.1 dice que el robot «permanezca en reposo seguro». REQ-12 dice solo que no se envía ningún comando, así que el robot sigue como estaba. | 1) Corregir el objetivo 4 de H1: el robot sigue como estaba. 2) Cambiar REQ-12 para que el robot pase a reposo. | |
| X-07 | **Qué comando corta el giro.** La prueba de REQ-15 y REQ-16 dice «`kwkL` durante la duración calibrada». Ni H1 ni la spec dicen qué comando se envía al acabar ese tiempo. Duplica P-09. | Decidir el comando de corte con el robot en la sesión 2 y escribirlo en REQ-15 y REQ-16 (y en el catálogo). | |

## B. H1 se contradice a sí mismo o con otras fuentes

| ID | Qué pasa | Opciones | Respuesta del equipo |
| --- | --- | --- | --- |
| X-01 | **Bluetooth o USB.** H1 §2.1 (alcance) dice solo «Bluetooth». REQ-20 y OPEN-07 dicen «Bluetooth o USB». El profesor dijo el 26/10 que se comunica por Bluetooth. | 1) Cambiar el alcance a «Bluetooth o USB». 2) Dejar solo Bluetooth y quitar USB de REQ-20. Depende de P-02. | |
| X-02 | **Baudios.** CTX-07 da 115200 como dato documentado. `capacidades-bittle.md` §8 dice que falta la velocidad y el formato de respuesta. | Medirlo con el robot en la sesión 2. Hasta entonces, CTX-07 debe decir «por confirmar». | |
| X-03 | **¿Acordado con el cliente?** CTX-01 dice «comprobado y acordado con el cliente». `capacidades-bittle.md` §9 dice «En estudio, no decidido». | Mirar la respuesta del cliente y dejar las dos fuentes con la misma frase. Si no hay acuerdo escrito, preguntar al profesor por Teams. | |
| X-04 | **Motor de voz dentro o fuera del sistema.** H1 §2.4 elige un motor local sin conexión, pero OPEN-06 sigue abierto y `spec.md` no fija tecnología. H1 §2.2 pone el motor dentro del sistema; REQ-18 lo trata como dependencia externa. | Decidir si el motor es parte del sistema o una dependencia, y alinear §2.2, §2.4 y REQ-18. Cerrar OPEN-06 cuando se elija el motor (P-01). | |
| X-05 | **Conteos de H1 §8.** Dice «34 requisitos» (hay 35, REQ-01 a REQ-35) y «OPEN-01 a OPEN-10» (hay OPEN-01 a OPEN-12). | Corregir los dos números. | |

## C. Faltan cosas en los documentos de H2

| ID | Qué pasa | Opciones | Respuesta del equipo |
| --- | --- | --- | --- |
| Y-01 | **D-12 sin pendiente.** D-12 (no enviar los comandos `G` ni `g` del giroscopio) es una propuesta sin confirmar, pero ningún P-NN la recoge. T065 no sale marcada como bloqueada. | Añadir un P-NN para D-12 en `plan.md` y marcar T065 como bloqueada, o confirmar D-12 ahora. | |
| Y-05 | **Sitio para los prototipos de voz.** `plan.md` no dice dónde se guardan los resultados de I-1 e I-2 (latencia, aciertos con «Atenio», audio en disco). T047 propone `H3-implementacion-pruebas/prototipos/motor-voz.md`. | Aceptar esa ruta y añadirla a la estructura del proyecto en `plan.md`, u otra. | |
| Y-06 | **Prueba de batería baja.** La spec (Historia 7, REQ-33) la prueba solo con el robot simulado. `plan.md` la pone también en el nivel de robot físico. T078 la incluye como observación, sin criterio de aceptación. | 1) Quitarla del nivel físico en `plan.md`. 2) Añadir a la spec un criterio con el robot real. | |

## Resueltas

Al resolver una, se mueve aquí con la decisión, la fecha y el commit que la aplicó.

| ID | Decisión | Fecha | Commit |
| --- | --- | --- | --- |
| X-08 | Opción 1: se escribe la constitución con las reglas fijas de `CLAUDE.md`, `README.md` y H1, cada una con su fuente. Está en `.specify/memory/constitution.md` (la lee Spec Kit) y su copia `constitution.md` (esta carpeta). Decisión de Mario. | 2026-11-04 | commit «H2: constitución del proyecto» |
