# Verificación con el robot real (no es parte del programa)

Herramientas del **bloque C** para probar el Bittle de verdad y tomar medidas en las sesiones con el robot (T068 a T071, T080). **No forman parte de la implementación final**: el programa (`src/atenio/`) no las importa y sus pruebas no están en `tests/`.

Lo que se mide se anota en [`H4-demostracion-aceptacion/ensayos-fisicos.md`](../../H4-demostracion-aceptacion/ensayos-fisicos.md). Los CSV se guardan en `H4-demostracion-aceptacion/ensayos/`.

| Archivo | Para qué |
|---|---|
| `panel_robot.py` + `panel_robot.html` | **Panel con botones** en el navegador: una orden por clic, botón de PARADA, registro de lo que responde el robot y tabla de medidas. |
| `sesion_robot.py` | La misma idea en consola, escribiendo los comandos. |
| `medicion.py` | Lógica de medida que usa `sesion_robot.py`. |
| `test_*.py`, `conftest.py` | Pruebas de estas herramientas, sin robot. |

## Uso

Desde `H3-implementacion-pruebas/`, con el robot encendido y emparejado por Bluetooth:

```bash
python verificacion-robot/sesion_robot.py --listar
```
```bash
python verificacion-robot/panel_robot.py --puerto COM6
```

y abrir <http://localhost:8765>. Para salir, **Ctrl+C** en la terminal: envía la parada, guarda las medidas y libera el puerto. Solo un programa puede usar el puerto a la vez (cerrar la consola antes de abrir el panel y al revés).

Sin robot: `python verificacion-robot/panel_robot.py --simulado`.

## Pruebas

```bash
python -m pytest verificacion-robot
```

Las del programa siguen siendo `python -m pytest` (carpeta `tests/`).

## Qué mide el panel

| Columna | Qué es |
|---|---|
| Respuesta | Tiempo hasta que el robot devuelve la primera letra del comando (`k`, `d`). Es un **«recibido»**: con `kwkF` llega a los 0,2-0,4 s mientras el robot sigue andando. |
| Duración | Tiempo hasta que la persona pulsa «Ha terminado». Es la que va a `catalogo.json` (T033). |
| En marcha | Tiempo que estuvo en marcha hasta que se cortó con la parada u otra orden. |
