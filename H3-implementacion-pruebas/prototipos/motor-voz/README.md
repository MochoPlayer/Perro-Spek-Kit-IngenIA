# Prototipo I-1 / I-2 · motor de voz (P-01)

Mide en el portátil Vosk y Faster-Whisper con voz real, para que el equipo elija el motor (P-01, D-02, OPEN-01, OPEN-06).
Ruta propuesta en la discrepancia Y-05 y en `tasks.md` T047 y T048. **La conclusión está pendiente de la medida con voz real.**

## Preparar (una vez)

```powershell
py -3.12 -m pip install -r H3-implementacion-pruebas/prototipos/motor-voz/requirements.txt
```

Modelos en `prototipos/motor-voz/modelos/` (la carpeta está en `.gitignore`; no se suben):

- Vosk: `vosk-model-small-es-0.42` (español, pequeño), de <https://alphacephei.com/vosk/models>. Descomprimir en `modelos/`.
- Faster-Whisper `tiny` y `base` (int8, CPU): se bajan solos la primera vez en `modelos/`.

## Medir

Desde `H3-implementacion-pruebas/`, en una sala tranquila:

```powershell
py -3.12 -X utf8 prototipos/motor-voz/medir.py
```

1. El script calibra el ruido: 1 s en silencio.
2. Muestra una frase de `tests/frases/con_nombre.txt` y `encadenadas.txt` (27 frases). Pulsa Enter y di la frase.
3. Cada motor transcribe el mismo audio. En pantalla sale el texto, la latencia y si el intérprete da la orden esperada.
4. Enter guarda la frase; `r` la repite; `s` la salta; `q` termina.

Tras cada frase sale la duración de la grabación, la de la parte con voz y el pico de energía (RMS). Si la voz dura mucho menos que la frase dicha, la grabación se cortó pronto.

Opciones:

| Opción | Qué hace | Por defecto |
|---|---|---|
| `--mic` | Lista los micrófonos y pregunta cuál usar. `--mic lista` solo los lista; `--mic 1` usa el número 1. | el de Windows |
| `--silencio 0.9` | Silencio (s) que cierra la frase. Más largo = no corta pausas, pero suma a la latencia. | 0,9 s |
| `--prerrollo 0.3` | Audio (s) que se guarda antes del primer bloque con voz. | 0,3 s |
| `--max 10` | Número máximo de frases. | 27 |
| `--motores vosk-flujo,whisper-tiny` | Motores que se miden. | los 5 |

Para seguir dentro de la frase basta el 60 % del umbral de voz: las sílabas flojas del final («-tate») no la cortan.

Salida: `resultados-<fecha>.md` en esta carpeta, **solo texto** (frase, texto de cada motor, latencia, «Atenio», orden). El audio queda en memoria y se descarta (REQ-24).

## Qué se mide

| Motor | Qué es |
|---|---|
| `vosk` | Vosk, modelo pequeño de español, con el audio entero al final de la frase. |
| `vosk-flujo` | Vosk como funcionaría en el sistema: recibe el audio mientras se habla; solo cuenta el cierre. |
| `whisper-tiny`, `whisper-base` | Faster-Whisper en CPU (int8), español. |
| `whisper-base-pista` | `whisper-base` con «Atenio» como texto inicial (`initial_prompt`), para ayudarle con el nombre. |

- **Latencia** (REQ-21, < 1,5 s provisional): desde el último bloque con voz hasta tener la orden del intérprete. Incluye el silencio que cierra la frase (0,9 s por defecto): con 0,9 s, solo queda 0,6 s para transcribir. Falta el envío al robot (milisegundos, se mide aparte).
- **Órdenes acertadas** (REQ-22, ≥ 80 % provisional): el intérprete del equipo, sin cambios, da exactamente las órdenes esperadas.
- **«Atenio»**: es la primera palabra del texto (el intérprete lo exige, REQ-01).

## I-2 · audio solo en local, sin ficheros (REQ-24, OPEN-06)

- `audio.py` y `transcripcion.py` pasan el audio en memoria (bytes) a los dos motores. Ninguno de los dos usa la red al transcribir: los modelos están en el disco.
- Pruebas automáticas: `tests/unitarias/test_sin_audio_en_disco.py` (ninguna escritura de fichero durante una sesión con micrófono falso).
- Falta comprobarlo tras la sesión real: buscar ficheros de audio nuevos en la carpeta de trabajo.

## Historial

- 2026-11-04, primer intento: con 0,6 s de silencio y 0,2 s de prerrollo, todos los motores perdieron «siéntate» en «Atenio, siéntate» (por ejemplo «Atenio 100.»). La grabación se cortaba pronto. Se pasó a 0,9 s, 0,3 s de prerrollo y umbral más bajo para seguir en la frase. No se guardaron datos.

## Conclusión

Pendiente de la medida con voz real.
