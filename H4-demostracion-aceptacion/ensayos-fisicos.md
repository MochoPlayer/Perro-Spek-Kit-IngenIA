# Ensayos físicos con el Bittle

**Bloque C** ([`reparto-modulos.md`](../H3-implementacion-pruebas/reparto-modulos.md)). Aquí se anota lo que se mide con el robot real. Los huecos `____` los rellena el equipo **durante la sesión**: no se copian valores de internet ni de la IA (CLAUDE.md, «No inventes contenido»).

Cada valor medido se pasa después a `H3-implementacion-pruebas/datos/catalogo.json` (duraciones, T033) y a `datos/ajustes.json` (puerto, baudios, fin de línea, T046), quitando su `"provisional": true`.

## Cómo medir

Las herramientas están en [`H3-implementacion-pruebas/verificacion-robot/`](../H3-implementacion-pruebas/verificacion-robot/README.md) (no forman parte del programa). Desde `H3-implementacion-pruebas/`, con el entorno de Python activado:

```bash
python verificacion-robot/sesion_robot.py --listar
```

**Panel con botones** (recomendado): abre <http://localhost:8765> y se manda cada orden con un clic.
```bash
python verificacion-robot/panel_robot.py --puerto COM6
```

**Consola** (escribiendo los comandos):
```bash
python verificacion-robot/sesion_robot.py --puerto COM6
```

La consola pide la lista de seguridad (T068) y después:

| Tecla | Qué hace |
|---|---|
| `ksit` (un comando) | Lo envía y empieza a cronometrar |
| Enter | El robot ha terminado: guarda la duración |
| `-` | El comando no termina solo (marcha continua): se guarda sin duración |
| `p` | **Parada**: envía el comando de parada de `ajustes.json` |
| `n texto` | Añade una nota a la última medida |
| `q` | Sale y guarda el CSV en `H4-demostracion-aceptacion/ensayos/` |

Ctrl+C también envía la parada. La herramienta nunca envía `G` ni `g` (REQ-34, D-12). **Cada duración se mide 3 veces** y se apunta la media.

---

## Prueba de conexión · 04/11/2026

Primera conexión desde nuestro programa. **No es la sesión 2**: las duraciones se tomaron pulsando a mano y sin repetir, así que no sirven para `catalogo.json`. Datos en bruto: `ensayos/sesion-20261104-1153.csv` (consola) y `ensayos/panel-20261104-121705.csv` (panel, versión que tomaba la letra de respuesta como fin; ver punto 4).

Lo observado (pendiente de que el equipo lo confirme en la sesión 2):

1. **Conexión**: Bluetooth, dispositivo `Petoi-30AD`, puerto `COM6` en el portátil de la prueba (el número cambia en cada ordenador). Con 115200 baudios y fin de línea `\n` el robot obedece todos los comandos del Nivel 1.
2. **Al abrir el puerto el robot se reinicia** y escribe `* Start *`, `Bittle`, `N_240517`, `IMU`, `Servo:23.67`, `Skill`, `Ready!`, `g`, `d`. `N_240517` parece la versión del firmware (NyBoard, 17/05/2024): por confirmar.
3. El módulo Bluetooth manda bytes `0` sueltos; el enlace serie ya los descarta.
4. **Tras cada comando el robot devuelve su primera letra** (`k` tras `ksit`, `kwkF`…; `d` tras `d`), a veces precedida de `G` o `g`. Con `kwkF`, `kwkL`, `kwkR` y `ktrF` la `k` llega a los 0,2-0,4 s **mientras sigue andando**: es un «recibido», **no el fin de la acción**. Con `khi` llegó a los 3,5-5,4 s (¿al acabar el saludo?): por comprobar.
5. `kwkf` (con `f` minúscula) no es un comando: el robot devuelve `?wkf`.
6. Se cortaron `ktrF`, `kwkL` y `kwkR` en marcha enviando la parada (`d`) y el robot respondió `k`/`d`; según quien vigilaba, el robot obedeció todas las órdenes. Falta comprobar con calma que `d` lo para siempre (dato para P-05).

---

## Sesión 2 · Fecha: ____ · Asistentes: ____

### T068 · Lista de seguridad (REQ-28)

| ☐ | Comprobación | Firma |
|---|---|---|
| ☐ | Superficie lisa y sin obstáculos | ____ |
| ☐ | Una persona vigilando el robot todo el tiempo | ____ |
| ☐ | Batería cargada | ____ |

### T070 · Conexión (P-02, X-02)

| Vía | Puerto | Baudios | Fin de línea (`\n`, `\r\n`, ninguno) | ¿Funciona? | Notas |
|---|---|---|---|---|---|
| USB | ____ | ____ | ____ | ____ | |
| Bluetooth | ____ | ____ | ____ | ____ | ¿Emparejamiento? ____ |

### T069 · Duración de las órdenes del Nivel 1 (P-03, T033)

Comandos de `catalogo.json`. En las de marcha continua (`kwkF`, `kwkL`, `kwkR`, `ktrF`) se anota si para sola y, si no, con qué comando se corta.

| Orden | Comando | Medida 1 (s) | Medida 2 (s) | Medida 3 (s) | Media (s) | ¿Termina sola? | Qué devuelve el robot |
|---|---|---|---|---|---|---|---|
| siéntate (REQ-02) | `ksit` | | | | | | |
| levántate (REQ-03) | `kup` | | | | | | |
| camina (REQ-04) | `kwkF` | | | | | | |
| izquierda (REQ-05) | `kwkL` | | | | | | |
| derecha (REQ-06) | `kwkR` | | | | | | |
| para (REQ-07) | `krest` | | | | | | |
| túmbate (REQ-08) | `d` | | | | | | |
| saluda (REQ-09) | `khi` | | | | | | |
| equilíbrate (REQ-10) | `kbalance` | | | | | | |
| trota (REQ-11) | `ktrF` | | | | | | |

**Tiempo de marcha** que el equipo decide para `kwkF`, `kwkL`, `kwkR` y `ktrF` (D-06, R-04): ____ s.

### T071 · Comandos por confirmar (P-05, OPEN-03, OPEN-10)

| Prueba | Resultado | Notas |
|---|---|---|
| ¿Existe `khi` (saluda)? | ____ | |
| ¿Existe `ktrF` (trota)? | ____ | |
| `krest` durante una marcha: ¿para el robot? | ____ | |
| `d` durante una marcha: ¿para el robot? | ____ | |
| ¿Cuál se usa para la parada de emergencia y cuál para el reposo? (P-05, Y-03) | ____ | |
| Levantar el robot (`lifted`) y dejarlo (`dropped`): ¿para? | ____ | |
| Lista real de skills (`printSkillFileName()`) | ____ | |

### T080 · Órdenes opcionales (P-09, X-07)

| Orden | Qué medir | Resultado |
|---|---|---|
| baila (REQ-14) | Secuencia de comandos y duración de cada uno | ____ |
| media vuelta (REQ-15) | Tiempo de `kwkL` para girar 180° | ____ s |
| da una vuelta (REQ-16) | Tiempo de `kwkL` para girar 360° | ____ s |
| Corte del giro | Comando que corta `kwkL` al acabar | ____ |

### Incidencias

____
