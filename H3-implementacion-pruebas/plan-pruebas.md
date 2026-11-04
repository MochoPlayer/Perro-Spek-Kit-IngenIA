# H3 · Plan de pruebas: REQ y SC → pruebas → nivel → estado

**Fecha**: 2026-11-04 · **Rama**: `h2/speckit` · **Fuentes**: [`spec.md`](../H2-especificacion-planificacion/spec.md), [`plan.md`](../H2-especificacion-planificacion/plan.md) («Niveles de prueba», «REQ → componente → decisión»), [`tasks.md`](../H2-especificacion-planificacion/tasks.md) y el código de esta carpeta.

**Ejecución real** (desde `H3-implementacion-pruebas/`, Python 3.12.10):

```text
python -m pytest            → 263 passed in 0.29s
python -m pytest            → 263 passed in 0.27s   (segunda vez, mismo resultado: SC-007)
python -m pytest -m "pendiente or discrepancia"   → 67 passed (pruebas que dependen de algo sin decidir)
```

Sin robot, sin micrófono y sin puerto serie real (el enlace serie se prueba con el puerto falso `loop://` de `pyserial`).

> **Cómo leer este documento.** Una fila por cada REQ-01 a REQ-35 y por cada SC-001 a SC-012. Las rutas de las pruebas son relativas a `tests/` y van como `fichero::función`. Una prueba con parámetros cuenta como una función.
>
> **Niveles** (`plan.md`, «Niveles de prueba»): **U** unitaria · **IS** integración con robot simulado · **VR** integración con voz real · **RF** robot físico (sesión 2 y demo, H4) · **Insp** inspección.
>
> **Estado**:
> - **pasa**: hay prueba sin robot y pasa, sin depender de nada abierto.
> - **pasa · pendiente X**: la prueba pasa, pero usa un valor o una opción provisional de un pendiente (P-NN), una discrepancia (`discrepancias.md`) o un OPEN-NN. Se cierra cuando el equipo decida X. Esas pruebas llevan la marca `pendiente("P-NN")` o `discrepancia("ID")`.
> - **falta**: no hay prueba y se puede escribir ya.
> - **bloqueado por X**: no hay prueba (o solo una parte) porque falta una decisión del equipo o el robot.
>
> Las discrepancias y los P-NN **no se deciden aquí** (decisión de Mario, 04/11): quedan como «pendiente del equipo», con sus opciones en `discrepancias.md` y `plan.md`.

## Requisitos (REQ-01 a REQ-35)

| REQ | Prueba(s) | Nivel | Estado |
|---|---|---|---|
| REQ-01 | `unitarias/test_interprete.py::test_req01_frase_con_nombre_es_orden` (20 frases), `::test_req01_frase_sin_nombre_se_ignora` (20 frases), `::test_req01_atenio_debe_ir_al_principio`; `integracion/test_cadena.py::test_h1_las_20_frases_con_nombre_producen_un_comando`, `::test_h1_las_20_frases_sin_nombre_no_producen_comando` | U, IS | **pasa**. VR: bloqueado por P-01 (OPEN-01, T047). |
| REQ-02 | `integracion/test_cadena.py::test_h1_cada_orden_del_nivel_1_llega_como_su_comando[siéntate-ksit]`; `unitarias/test_interprete.py::test_req02_a_req16_texto_da_los_comandos_del_catalogo`; `unitarias/test_catalogo.py::test_orden_del_nivel_1_tiene_la_palabra_y_el_comando_de_spec` | U, IS | **pasa**. RF: falta (T072, bloqueado por P-02). |
| REQ-03 | Las mismas tres funciones, caso `levántate` → `kup` | U, IS | **pasa**. RF: falta (T072). |
| REQ-04 | Las mismas, caso `camina` → `kwkF` | U, IS | **pasa**. Tiempo de marcha: pendiente P-03. RF: falta (T072). |
| REQ-05 | Las mismas, caso `izquierda` → `kwkL` | U, IS | **pasa**. Tiempo de marcha: pendiente P-03. RF: falta (T072). |
| REQ-06 | Las mismas, caso `derecha` → `kwkR` | U, IS | **pasa**. Tiempo de marcha: pendiente P-03. RF: falta (T072). |
| REQ-07 | `unitarias/test_gestor_acciones.py::test_para_con_accion_en_curso_envia_krest_en_el_acto_y_no_se_encola`, `::test_para_con_robot_libre_envia_krest`; `unitarias/test_catalogo.py::test_solo_para_interrumpe`; `unitarias/test_interprete.py::test_req07_para_marca_interrumpe`; `integracion/test_cadena.py::test_h5_para_con_accion_en_curso_envia_krest_y_no_queda_en_cola` | U, IS | **pasa**. La cola tras «para» y «para» dentro de una frase (`test_para_vacia_la_cola`, `test_d10_*`, `test_h5_para_con_ordenes_en_cola_las_descarta`): pendiente P-04 / OPEN-12. RF: falta (T072). |
| REQ-08 | `integracion/test_cadena.py::test_h1_cada_orden_del_nivel_1_llega_como_su_comando[túmbate-d]` y las mismas de REQ-02 | U, IS | **pasa**. RF: falta (T072). |
| REQ-09 | Las mismas, caso `saluda` → `khi` | U, IS | **pasa**. El comando `khi` está por confirmar en el robot (OPEN-03, T071). |
| REQ-10 | Las mismas, caso `equilíbrate` → `kbalance` | U, IS | **pasa**. RF: falta (T072). |
| REQ-11 | Las mismas, caso `trota` → `ktrF` | U, IS | **pasa**. El comando `ktrF` está por confirmar en el robot (OPEN-03, T071). |
| REQ-12 | `unitarias/test_interprete.py::test_req12_sin_sentido_no_entendida_con_aviso`, `::test_req12_ruido_sin_atenio_se_ignora_sin_aviso`; `integracion/test_cadena.py::test_h2_20_entradas_sin_sentido_ningun_comando_y_aviso_cada_vez`; `unitarias/test_gestor_acciones.py::test_avisos_del_interprete_pasan_a_la_interfaz` | U, IS | **pasa · pendiente Y-02, Y-04, X-06**. Las pruebas usan la opción 1 de Y-02 (sin «Atenio» se ignora todo, sin aviso). |
| REQ-13 | `unitarias/test_interprete.py::test_req13_fuera_del_catalogo_con_aviso`, `::test_req13_sigueme_da_aviso_de_orden_no_disponible`; `integracion/test_cadena.py::test_h2_10_ordenes_fuera_del_catalogo_ningun_comando_y_aviso_cada_vez` | U, IS | **pasa · pendiente Y-02** (regla que separa REQ-12 de REQ-13). |
| REQ-14 | `unitarias/test_interprete.py::test_req14_baila_sin_secuencia_es_orden_no_disponible`; `unitarias/test_catalogo.py::test_opcionales_de_nivel_2` | U | **bloqueado por P-09** (OPEN-08: no hay secuencia de «baila»; hoy da «orden no disponible»). Falta `integracion/test_opcionales.py` (T066). RF: T081. |
| REQ-15 | `unitarias/test_catalogo.py::test_opcionales_de_nivel_2`; `unitarias/test_interprete.py::test_req02_a_req16_texto_da_los_comandos_del_catalogo[media vuelta-…]` | U | **bloqueado por P-09** (duración del giro, OPEN-04) y X-07 (comando de corte). RF: T081 (5 intentos, ±45°). |
| REQ-16 | Las mismas, caso `da una vuelta` → `kwkL`, `kwkL`; `unitarias/test_gestor_acciones.py::test_orden_con_varios_pasos_los_envia_uno_tras_otro` | U | **bloqueado por P-09** y X-07. RF: T081. |
| REQ-17 | — | VR | **bloqueado por P-01** (no existe `audio.py`; T051). |
| REQ-18 | `unitarias/test_interprete.py::test_req18_normalizacion_da_el_mismo_resultado` y todas las del intérprete (texto → orden) | U, Insp | **pasa · pendiente P-01, X-04**: el intérprete propio pasa; la transcripción existente (`transcripcion.py`, T049, T050) está bloqueada por P-01. |
| REQ-19 | `unitarias/test_gestor_acciones.py::test_orden_interpretada_se_publica`, `::test_avisos_del_interprete_pasan_a_la_interfaz`, `::test_tras_perder_la_conexion_las_ordenes_avisan_robot_no_conectado` (evento de estado de conexión) | U | **bloqueado por P-06** (no existe la interfaz; T055, T056). Solo se prueba la parte de eventos. |
| REQ-20 | `integracion/test_cadena.py::test_h3_el_simulado_registra_la_cadena_exacta_y_la_hora`, `::test_h1_cada_orden_del_nivel_1_llega_como_su_comando`; `unitarias/test_enlace_simulado.py::test_registra_hora_y_cadena_exacta`; `unitarias/test_enlace_serie.py::test_envia_cadena_con_fin_de_linea`, `::test_conecta_y_desconecta`, `::test_lee_lineas_completas_y_guarda_el_resto` | U, IS | **pasa**. Puerto, baudios y USB o Bluetooth con el robot: bloqueado por P-02 (X-01, X-02; T070, T072). |
| REQ-21 | `integracion/test_cadena.py::test_h1_cada_orden_del_nivel_1_llega_como_su_comando` (con reloj simulado el comando sale en el instante 0) | IS | **falta** la prueba de software con reloj real: 20 mediciones (T020). VR (20 mediciones con voz): bloqueado por P-01 (T052). |
| REQ-22 | — | VR | **bloqueado por P-01** (T053: 20 intentos por orden). |
| REQ-23 | `unitarias/test_interprete.py::test_req23_sigue_funcionando_tras_20_entradas_invalidas`; `integracion/test_cadena.py::test_h2_orden_valida_tras_20_entradas_invalidas` | U, IS | **pasa**. |
| REQ-24 | — | U, Insp | **bloqueado por P-01** (no existe captura ni transcripción; T049 con motor falso, T054 inspección). |
| REQ-25 | `unitarias/test_gestor_acciones.py::test_sin_conexion_no_envia_y_avisa`, `::test_sin_conexion_no_hay_reposo_ni_aviso`, `::test_boton_sin_conexion_activa_la_parada_y_avisa`; `unitarias/test_enlace_simulado.py::test_sin_conexion_no_envia`; `unitarias/test_enlace_serie.py::test_sin_conexion_envio_falso`; `integracion/test_cadena.py::test_h6_sin_conexion_no_envia_y_avisa` | U, IS | **pasa**. Pérdida durante una acción (`test_fallo_de_envio_durante_una_accion_…`, `test_tras_perder_la_conexion_…`): pendiente P-08. RF: T076. |
| REQ-26 | Todo el conjunto (263 pruebas) sin robot, dos veces con el mismo resultado; `unitarias/test_enlace_simulado.py` | U, IS | **pasa**. Faltan el guardián de T012, la prueba T026 y el script T027. |
| REQ-27 | — | RF | **bloqueado por P-07** (no existe `principal.py` ni la guía de instalación; T057, T058). |
| REQ-28 | — | Insp | **falta**: lista de seguridad antes de cada sesión con el robot (T068, H4). No es una prueba automática. |
| REQ-29 | `unitarias/test_interprete.py::test_req29_encadenadas_en_el_orden_dicho`, `::test_req29_orden_fuera_del_catalogo_se_salta_con_aviso`, `::test_req29_todas_fuera_del_catalogo`, `::test_req29_maximo_de_ordenes_por_frase`; `unitarias/test_gestor_acciones.py::test_dos_ordenes_en_una_frase_…`, `::test_tres_ordenes_en_una_frase`; `integracion/test_cadena.py::test_h4_frases_encadenadas_llegan_en_el_orden_dicho`, `::test_h4_cada_comando_sale_al_terminar_el_anterior`, `::test_h4_orden_fuera_del_catalogo_se_salta_con_aviso` | U, IS | **pasa · pendiente P-03** (duraciones de prueba de 1 s, máximo por frase, palabras de enlace). RF: T075. |
| REQ-30 | `unitarias/test_gestor_acciones.py::test_boton_envia_el_comando_de_parada_y_vacia_la_cola`, `::test_con_parada_activa_ninguna_de_10_ordenes_produce_comando`, `::test_para_tambien_se_ignora_con_parada_activa`, `::test_segundo_clic_desactiva_y_la_siguiente_orden_se_ejecuta`, `::test_parada_manda_sobre_el_reposo_por_inactividad`, `::test_boton_desde_reposo`; `integracion/test_cadena.py::test_h5_parada_de_emergencia_completa` | U, IS | **pasa · pendiente P-05, Y-03** (comando de parada `d` provisional). El botón de la interfaz: bloqueado por P-06. RF: T073. |
| REQ-31 | `unitarias/test_gestor_acciones.py::test_reposo_tras_T_sin_ordenes_sin_aviso`, `::test_reposo_se_envia_una_sola_vez`, `::test_T_cuenta_desde_la_ultima_orden`, `::test_orden_valida_saca_del_reposo_y_se_ejecuta`, `::test_T_por_defecto_es_el_de_la_demostracion`; `integracion/test_cadena.py::test_h7_reposo_tras_T_y_una_orden_lo_despierta` | U, IS | **pasa · pendiente P-05** (comando de reposo `krest` provisional, OPEN-11). RF: T077. |
| REQ-32 | `unitarias/test_gestor_acciones.py::test_tres_ordenes_con_robot_ocupado_se_envian_en_orden_de_llegada`; `integracion/test_cadena.py::test_h4_tres_ordenes_con_robot_ocupado_en_orden_de_llegada`, `::test_catalogo_real_marcha_sin_duracion_bloquea_la_cola_hasta_para` | U, IS | **pasa · pendiente P-03** (fin de acción por duración; con el catálogo real una marcha sin duración no termina sola). RF: T075. |
| REQ-33 | `unitarias/test_gestor_acciones.py::test_low_power_produce_aviso_de_bateria_baja`, `::test_otras_lineas_del_robot_no_avisan`; `unitarias/test_enlace_simulado.py::test_inyecta_low_power_y_lo_detecta`; `unitarias/test_enlace_serie.py::test_deteccion_bateria_baja`; `integracion/test_cadena.py::test_h7_low_power_avisa_de_cargar_el_robot` | U, IS | **pasa**. RF (T078): pendiente Y-06. |
| REQ-34 | `unitarias/test_enlace_serie.py::test_nunca_envia_giroscopio`; `unitarias/test_enlace_simulado.py::test_rechaza_giroscopio`; `unitarias/test_catalogo.py::test_todos_los_comandos_estan_en_la_lista_segura` | U | **pasa · pendiente Y-01** (D-12 sin confirmar). Que el robot se pare al cogerlo solo se ve con el robot (T079, OPEN-10). |
| REQ-35 | `unitarias/test_interprete.py::test_req35_solo_atenio`, `::test_req35_orden_sin_nombre_dentro_de_5_s`, `::test_req35_justo_a_los_5_s_todavia_vale`, `::test_req35_despues_de_5_s_se_ignora` y 7 más `test_req35_*`; `integracion/test_cadena.py::test_h1_atenio_solo_y_orden_dentro_de_la_espera`, `::test_h1_atenio_solo_sin_orden_vuelve_a_la_escucha_normal` | U, IS | **pasa** (5 s provisional, OPEN-02, en `ajustes.json`). Una frase no válida dentro de la espera: pendiente Y-02. |

## Criterios de éxito (SC-001 a SC-012)

| SC | Prueba(s) | Nivel | Estado |
|---|---|---|---|
| SC-001 | — (ensayo de la demo, T074) | VR, RF | **bloqueado por P-01, P-02, P-06 y P-07**. La lógica (dos órdenes válidas y una no reconocida) ya pasa sin robot: SC-002 y SC-005. |
| SC-002 | `integracion/test_cadena.py::test_h1_cada_orden_del_nivel_1_llega_como_su_comando` (10 casos) | IS | **pasa**. |
| SC-003 | — | VR | **bloqueado por P-01** (T053). |
| SC-004 | — | IS, VR | **falta** la parte de software con reloj real (T020); voz real: **bloqueado por P-01** (T052). |
| SC-005 | `integracion/test_cadena.py::test_h1_las_20_frases_sin_nombre_no_producen_comando`, `::test_h2_20_entradas_sin_sentido_ningun_comando_y_aviso_cada_vez` | IS | **pasa · pendiente Y-02, Y-04**. |
| SC-006 | `integracion/test_cadena.py::test_h2_orden_valida_tras_20_entradas_invalidas` | IS | **pasa**. |
| SC-007 | Todo el conjunto ejecutado dos veces el 04/11: 263 y 263, mismo resultado | U, IS | **pasa**. Falta el script que lo hace solo (T027). |
| SC-008 | — | VR, Insp | **bloqueado por P-01** (T049, T054). |
| SC-009 | `integracion/test_cadena.py::test_h4_frases_encadenadas_llegan_en_el_orden_dicho`, `::test_h4_orden_fuera_del_catalogo_se_salta_con_aviso`; `unitarias/test_gestor_acciones.py::test_dos_ordenes_en_una_frase_…`, `::test_tres_ordenes_en_una_frase` | U, IS | **pasa · pendiente P-03**. |
| SC-010 | `integracion/test_cadena.py::test_h4_tres_ordenes_con_robot_ocupado_en_orden_de_llegada`; `unitarias/test_gestor_acciones.py::test_tres_ordenes_con_robot_ocupado_se_envian_en_orden_de_llegada` | U, IS | **pasa · pendiente P-03**. |
| SC-011 | `integracion/test_cadena.py::test_h5_parada_de_emergencia_completa`; `unitarias/test_gestor_acciones.py::test_con_parada_activa_ninguna_de_10_ordenes_produce_comando`, `::test_segundo_clic_desactiva_y_la_siguiente_orden_se_ejecuta` | U, IS | **pasa · pendiente P-05, Y-03**. |
| SC-012 | `integracion/test_cadena.py::test_h5_para_con_accion_en_curso_envia_krest_y_no_queda_en_cola`; `unitarias/test_gestor_acciones.py::test_para_con_accion_en_curso_envia_krest_en_el_acto_y_no_se_encola` | U, IS | **pasa**. |

## Resumen de cobertura (pruebas sin robot)

| Estado | REQ | SC |
|---|---|---|
| pasa | 17: REQ-01 a REQ-11, REQ-20, REQ-23, REQ-25, REQ-26, REQ-33, REQ-35 | 4: SC-002, SC-006, SC-007, SC-012 |
| pasa · pendiente del equipo | 8: REQ-12, REQ-13, REQ-18, REQ-29 a REQ-32, REQ-34 | 4: SC-005, SC-009, SC-010, SC-011 |
| falta (se puede hacer ya) | 2: REQ-21 (T020), REQ-28 (T068, inspección) | 1: SC-004 (parte de software) |
| bloqueado | 8: REQ-14, REQ-15, REQ-16 (P-09); REQ-17, REQ-22, REQ-24 (P-01); REQ-19 (P-06); REQ-27 (P-07) | 4: SC-001, SC-003, SC-008 (P-01 y otros); SC-004 (voz real, P-01) |

**25 de 35 REQ** tienen una prueba sin robot que pasa (17 sin condiciones y 8 con un valor u opción provisional). SC-004 cuenta en «falta» y en «bloqueado» porque tiene las dos partes.

## Lo que falta para cerrar H3 (en orden)

Orden: primero lo que no depende de nadie, después lo que necesita una decisión del equipo, al final lo que necesita el robot.

1. **Guardián sin robot** (T012, T026): `conftest.py` hace fallar cualquier prueba que abra un puerto serie real o el micrófono. Cierra el principio I de la constitución (hallazgo D3 de `coherencia.md`).
2. **Script de doble ejecución** (T027): ejecuta el conjunto dos veces y compara. Cierra SC-007 sin pasos a mano.
3. **Latencia de software** (T020): 20 mediciones con reloj real, texto → registro del simulado, todas < 1,5 s `[provisional]`. Cierra la parte de software de REQ-21 y SC-004.
4. **Prueba de eventos** (T009, T055): `test_eventos.py` con los cuatro tipos de evento, y publicar también el estado de conexión al conectar (hallazgo U2 de `coherencia.md`).
5. **`principal.py` con el robot simulado** (T019, T045): monta la cadena como la clase `Cadena` de las pruebas y elige enlace real o simulado con un ajuste.
6. **`casos-de-prueba.md`** (T004, T041): el entregable que pide el `README.md` de H3. Este documento sirve de base si el equipo lo acepta.
7. **Revisión del código** por el equipo (T042) → `revision-codigo.md`.
8. **Decisiones del equipo que cierran pruebas ya escritas** (las 67 marcadas): Y-02 y Y-04 (REQ-12, REQ-13, SC-005), P-03 (REQ-29, REQ-32, SC-009, SC-010), P-04 (REQ-07, cola), P-05 y Y-03 (REQ-30, REQ-31, SC-011), P-08 (REQ-25), Y-01 (REQ-34). Al decidir, se quita la marca o se cambia la prueba.
9. **Decisiones que desbloquean código nuevo**: P-01 (motor de voz → REQ-17, REQ-18, REQ-22, REQ-24, SC-003, SC-008; tareas T047 a T054), P-06 (interfaz → REQ-19, botón de REQ-30; T056), P-07 (REQ-27; T057, T058), P-09 (REQ-14 a REQ-16; T066, T067).
10. **Sesión 2 con el robot** (H4, no bloquea H3): T068 a T071 y T080 dan las medidas que cierran P-02, P-03, P-05 y P-09.

Los pasos 1 a 7 dejan H3 entregable con lo que exige su `README.md` (código, pruebas reproducibles sin robot y revisión). Los pasos 8 a 10 dependen del equipo o del robot.
