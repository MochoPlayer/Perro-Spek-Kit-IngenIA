# Ensayos físicos con el Bittle

**Bloque C** ([`reparto-modulos.md`](../H3-implementacion-pruebas/reparto-modulos.md)). Aquí se anota lo que se mide con el robot real. Los huecos `____` los rellena el equipo **durante la sesión**: no se copian valores de internet ni de la IA (CLAUDE.md, «No inventes contenido»).

Cada valor medido se pasa después a `H3-implementacion-pruebas/datos/catalogo.json` (duraciones, T033) y a `datos/ajustes.json` (puerto, baudios, fin de línea, T046), quitando su `"provisional": true`.

## Cómo medir

Desde `H3-implementacion-pruebas/` (con el entorno de Python activado):

```bash
python herramientas/sesion_robot.py --listar
```
```bash
python herramientas/sesion_robot.py --puerto COM5
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
