# H3 · Implementación y pruebas

**Entregable:** código ejecutable y pruebas en el repositorio.

**Mínimo exigido:** implementación generada con apoyo de IA, revisión del código y **pruebas reproducibles sin necesidad del robot físico**.

**Reparto del trabajo:** [`reparto-modulos.md`](reparto-modulos.md) (interfaz, intérprete, órdenes y robot, y bloque común). **Estado de cada requisito:** [`plan-pruebas.md`](plan-pruebas.md).

## Cómo instalar y ejecutar

> Parcial (T058): la voz funciona con el motor provisional de `ajustes.json` (P-01 sigue pendiente) y para un solo portátil (P-07 sin decidir). La interfaz es una página web local (D-07); P-06 sigue pendiente de confirmar por el equipo.

**Requisitos**: Python 3.12 (probado con 3.12.10) en el portátil. No hace falta internet ni el robot.

1. Instalar las dependencias (una vez), desde esta carpeta (`H3-implementacion-pruebas/`):
   ```
   python -m pip install -r requirements.txt
   ```
2. Pasar las pruebas (no usan robot, micrófono ni red; solo `127.0.0.1` en las del servidor):
   ```
   python -m pytest
   ```
3. Arrancar el programa con el robot simulado, desde `H3-implementacion-pruebas/src/`:
   ```
   cd src
   python -m atenio --simulado
   ```
   Se abre el navegador en `http://127.0.0.1:8642/`. Para salir: `Ctrl+C` en la terminal.
   Con voz: `py -3.12 -X utf8 -m atenio --simulado --voz` (sin `-I`: numpy está en el site-packages del usuario). Hace falta
   `requirements-voz.txt` y el modelo en `prototipos/motor-voz/modelos` (ver `prototipos/motor-voz/README.md`).
4. Probarlo en la página. La palabra de activación es **«Perro»** (ajuste `palabra_activacion` de `datos/ajustes.json`; Z-01):
   - **Botón redondo del centro**: enciende y apaga el micro. Encendido: relleno, 🎤 y «Escuchando». Apagado: contorno, 🔇 y «Micro apagado».
     Con `--voz` el programa arranca con el micro encendido; sin `--voz`, apagado, y el primer clic carga el motor de voz («Encendiendo…», unos segundos).
   - **Onda de voz** (debajo del botón): el nivel del micrófono, 20 veces por segundo. En silencio queda casi plana; al hablar sube.
     Al encender, el primer segundo calibra el ruido de la sala (no hables). Después sale la línea discontinua «umbral de voz»:
     las barras que la pasan se pintan en azul y cuentan como voz. Solo viajan números (RMS), nunca audio (REQ-24).
   - **Lo último que oí**: la última frase reconocida (de la voz o de la caja).
   - **Órdenes**: lo más nuevo arriba, «hora · orden · comando» (por ejemplo `12:04:36 camina kwkF`). Los avisos van en la misma lista, en ámbar.
     La orden se muestra con su nombre del catálogo («Perro, sentado» sale como «siéntate»).
   - Escribir `Perro, siéntate` en la caja pequeña y pulsar **Enviar**: sale «siéntate · ksit». `Perro, vuela` → aviso «orden no disponible: «vuela»».
     `hola` o `Atenio, siéntate` (sin «Perro») → no pasa nada (REQ-01).
   - **■ Parada** (arriba a la derecha): se envía `d`, el botón pasa a «▶ Quitar parada» y sale una banda roja «PARADA ACTIVA»; las órdenes se bloquean. Otro clic desbloquea (REQ-30).

**Opciones de `python -m atenio`**

| Opción | Qué hace |
|---|---|
| `--simulado` | Robot simulado (lo que dice `datos/ajustes.json`, clave `enlace`, si no se pone nada). |
| `--serie` | Robot real por el puerto serie de `ajustes.json` (`puerto`, `baudios`). Hoy `puerto` es `null` (OPEN-07): la página muestra «Robot no conectado». |
| `--voz` | Arranca con el micro encendido (`atenio.escucha`). Si el motor o el modelo faltan, avisa y sigue con el micro apagado. Sin `--voz` el micro arranca apagado y se enciende con el botón. |
| `--puerto N` | Puerto de la página (por defecto 8642). Si está ocupado, el programa lo dice y sale. |
| `--sin-navegador` | No abre el navegador. |

## Flujo de trabajo

Cada caja indica en cursiva el documento que produce. Leyenda debajo del diagrama.

```mermaid
flowchart TB
  classDef eq fill:#ffffff,stroke:#334155,color:#0f172a
  classDef ia fill:#ede9fe,stroke:#7c3aed,color:#2e1065
  classDef check fill:#fef3c7,stroke:#d97706,color:#78350f
  classDef hito fill:#0f172a,stroke:#0f172a,color:#ffffff
  classDef par stroke-dasharray:5 4

  subgraph S3["3 · H3 — Implementar y probar"]
    direction LR
    Q["Casos de prueba<br/><i>casos-de-prueba.md</i>"]:::eq
    R["Implementar<br/><i>src/</i>"]:::ia
    S{"¿Pasan las pruebas<br/>sin robot?<br/><i>tests/</i>"}:::check
    T["Revisión de código<br/><i>revision-codigo.md</i>"]:::eq
    M3(["H3"]):::hito
    class Q,R par
    Q & R --> S -- sí --> T --> M3
    S -- no --> R
  end

  subgraph LEY["Leyenda"]
    direction LR
    L1["Tarea del equipo"]:::eq
    L2["La genera la IA,<br/>el equipo revisa"]:::ia
    L3{"Control"}:::check
    L4(["Entrega"]):::hito
    L5["Borde discontinuo:<br/>en paralelo"]:::eq
    L6["Paso<br/><i>documento que produce</i>"]:::eq
    class L5 par
    L1 ~~~ L2 ~~~ L3 ~~~ L4 ~~~ L5 ~~~ L6
  end

  style LEY fill:#ffffff,stroke:#cbd5e1,color:#334155
  style S3 fill:#f8fafc,stroke:#cbd5e1,color:#334155
  S3 ~~~ LEY
```

### Pasos

**A la vez:**
- [ ] Diseñar los casos de prueba → `casos-de-prueba.md`
- [ ] Implementar el primer incremento con IA (`/speckit.implement`) → `src/`

**Después:**
- [ ] Pruebas reproducibles sin el robot → `tests/`. Si fallan, se vuelve a implementar.
- [ ] Revisión del código → `revision-codigo.md`

> La ubicación exacta de `src/` y `tests/` se fija en `plan.md`.

> El detalle de este hito se completará cuando se presente en clase.
