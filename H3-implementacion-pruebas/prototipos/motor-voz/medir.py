"""Prototipo I-1 (plan.md, T047): mide Vosk y Faster-Whisper con voz real en este portátil.

Muestra una frase de tests/frases/, la persona la dice, cada motor la transcribe y se guarda SOLO texto en
resultados-<fecha>.md (REQ-24: el audio queda en memoria y se descarta). Uso: ver README.md de esta carpeta.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

CARPETA = Path(__file__).resolve().parent
H3 = CARPETA.parents[1]
sys.path.insert(0, str(H3 / "src"))

from atenio.audio import PRERROLLO_S, SILENCIO_FIN_S, CapturaMicrofono, DetectorDeFrase, Frase, rms  # noqa: E402
from atenio.catalogo import Catalogo, cargar_catalogo, normalizar  # noqa: E402
from atenio.interprete import Interprete  # noqa: E402
from atenio.modelos import TipoInterpretacion  # noqa: E402
from atenio.transcripcion import Transcriptor, TranscriptorVosk, TranscriptorWhisper  # noqa: E402

LIMITE_LATENCIA_S = 1.5  # REQ-21, provisional
OBJETIVO_ACIERTOS = 0.80  # REQ-22, provisional
MODELOS = CARPETA / "modelos"
MODELO_VOSK = MODELOS / "vosk-model-small-es-0.42"
FICHEROS_FRASES = ("con_nombre.txt", "encadenadas.txt")
MOTORES_POR_DEFECTO = "vosk,vosk-flujo,whisper-tiny,whisper-base,whisper-base-pista"


@dataclass
class Medida:
    motor: str
    texto: str
    latencia_s: float  # fin de la voz → orden interpretada (incluye la espera de silencio)
    transcripcion_s: float
    atenio: bool  # «atenio» es la primera palabra (lo que exige el intérprete, REQ-01)
    orden_ok: bool
    obtenido: str


@dataclass
class Resultado:
    frase: str
    esperado: tuple[str, ...]
    duracion_s: float  # toda la grabación
    voz_s: float  # parte con voz
    medidas: list[Medida] = field(default_factory=list)


def leer_frases(nombres=FICHEROS_FRASES) -> list[tuple[str, tuple[str, ...]]]:
    frases = []
    for nombre in nombres:
        for linea in (H3 / "tests" / "frases" / nombre).read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            texto, ids = linea.split("=>")
            frases.append((texto.strip(), tuple(i.strip() for i in ids.split(","))))
    return frases


class VoskEnFlujo:
    """Vosk como funcionaría en el sistema: recibe el audio mientras se habla y al final solo cierra.

    Se pasa el audio entero sin contar ese tiempo (en vivo ocurre durante la frase; vale si el motor va más
    rápido que el tiempo real: se anota `durante_s`) y se mide solo el cierre (`terminar`).
    """

    def __init__(self, base: TranscriptorVosk):
        self.nombre = "vosk-flujo"
        self._base = base
        self.durante_s = 0.0

    def transcribir(self, audio: bytes) -> str:
        flujo = self._base.flujo()
        t0 = time.perf_counter()
        flujo.aceptar(audio)
        self.durante_s = time.perf_counter() - t0
        return flujo.terminar()


_VOSK: dict[str, TranscriptorVosk] = {}


def crear_motor(nombre: str) -> Transcriptor:
    if nombre in ("vosk", "vosk-flujo"):
        if "vosk" not in _VOSK:
            _VOSK["vosk"] = TranscriptorVosk(MODELO_VOSK)
        return _VOSK["vosk"] if nombre == "vosk" else VoskEnFlujo(_VOSK["vosk"])
    if nombre in ("whisper-tiny", "whisper-base"):
        return TranscriptorWhisper(nombre.split("-")[1], carpeta_modelos=MODELOS)
    if nombre in ("whisper-tiny-pista", "whisper-base-pista"):
        return TranscriptorWhisper(nombre.split("-")[1], carpeta_modelos=MODELOS, pista="Atenio", nombre=nombre)
    raise SystemExit(f"motor desconocido: {nombre}")


def evaluar(catalogo: Catalogo, texto: str, esperado: tuple[str, ...]) -> tuple[bool, bool, str]:
    """(¿«Atenio» primera palabra?, ¿orden correcta?, lo que da el intérprete)."""
    palabras = normalizar(texto).split()
    atenio = bool(palabras) and palabras[0] == "atenio"
    r = Interprete(catalogo).interpretar(texto, ahora=0.0)  # intérprete nuevo: sin estado de REQ-35
    ids = tuple(o.id for o in r.ordenes)
    obtenido = ", ".join(ids) if r.tipo is TipoInterpretacion.ORDENES else r.tipo.value
    return atenio, r.tipo is TipoInterpretacion.ORDENES and ids == esperado, obtenido


def medir_frase(frase: Frase, texto_esperado: str, esperado, motores, catalogo) -> Resultado:
    resultado = Resultado(texto_esperado, esperado, frase.duracion_s, frase.voz_s)
    espera_silencio = frase.cierre - frase.fin_voz
    for motor in motores:
        t0 = time.perf_counter()
        texto = motor.transcribir(frase.audio)
        t1 = time.perf_counter()
        atenio, ok, obtenido = evaluar(catalogo, texto, esperado)
        t2 = time.perf_counter()
        durante = getattr(motor, "durante_s", 0.0)  # vosk-flujo: lo procesado mientras se habla
        if durante > frase.duracion_s:
            print(f"  AVISO {motor.nombre}: va más lento que el tiempo real; su latencia queda corta")
        t0 += durante
        resultado.medidas.append(
            Medida(motor.nombre, texto, espera_silencio + (t2 - t0), t1 - t0, atenio, ok, obtenido)
        )
    return resultado


def _celda(texto: str) -> str:
    return texto.replace("|", "\\|") or "(vacío)"


def _coma(x: float, decimales: int = 2) -> str:
    return f"{x:.{decimales}f}".replace(".", ",")


def resumen(resultados: list[Resultado], motores: list[str]) -> list[str]:
    lineas = [
        "| Motor | Frases | Latencia media (s) | Latencia máx. (s) | < 1,5 s | Órdenes acertadas | «Atenio» reconocido | Transcripción media (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nombre in motores:
        ms = [m for r in resultados for m in r.medidas if m.motor == nombre]
        if not ms:
            continue
        lat = [m.latencia_s for m in ms]
        n = len(ms)
        bajo = sum(x < LIMITE_LATENCIA_S for x in lat)
        ok = sum(m.orden_ok for m in ms)
        at = sum(m.atenio for m in ms)
        lineas.append(
            f"| {nombre} | {n} | {_coma(statistics.mean(lat))} | {_coma(max(lat))} | {bajo}/{n} | "
            f"{ok}/{n} ({round(100 * ok / n)} %) | {at}/{n} ({round(100 * at / n)} %) | "
            f"{_coma(statistics.mean(m.transcripcion_s for m in ms))} |"
        )
    return lineas


def escribir(salida: Path, cabecera: list[str], resultados: list[Resultado], motores: list[str]) -> None:
    lineas = list(cabecera)
    lineas += ["", "## Resumen", ""] + resumen(resultados, motores)
    lineas += [
        "",
        f"Criterios provisionales: REQ-21 latencia < {_coma(LIMITE_LATENCIA_S, 1)} s; REQ-22 ≥ {round(OBJETIVO_ACIERTOS * 100)} % de órdenes acertadas.",
        "",
        "## Detalle por frase",
        "",
        "| # | Frase esperada | Esperado | Grabación / voz (s) | Motor | Texto del motor | Latencia (s) | Transcripción (s) | «Atenio» | Intérprete | Acierto |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(resultados, 1):
        for m in r.medidas:
            lineas.append(
                f"| {i} | {_celda(r.frase)} | {', '.join(r.esperado)} | {_coma(r.duracion_s)} / {_coma(r.voz_s)} | {m.motor} | {_celda(m.texto)} | "
                f"{_coma(m.latencia_s)} | {_coma(m.transcripcion_s)} | {'sí' if m.atenio else 'no'} | "
                f"{_celda(m.obtenido)} | {'sí' if m.orden_ok else 'no'} |"
            )
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def ruta_resultados() -> Path:
    base = CARPETA / f"resultados-{datetime.now():%Y-%m-%d}.md"
    n = 2
    ruta = base
    while ruta.exists():
        ruta = base.with_name(f"{base.stem}-{n}.md")
        n += 1
    return ruta


def ejecutar(
    frases,
    motores: list[Transcriptor],
    obtener_frase: Callable[[int, str], Frase | None],
    salida: Path,
    cabecera: list[str],
    preguntar: Callable[[str], str] = input,
) -> list[Resultado]:
    catalogo = cargar_catalogo()
    nombres = [m.nombre for m in motores]
    resultados: list[Resultado] = []
    i = 0
    while i < len(frases):
        texto, esperado = frases[i]
        print(f"\n[{i + 1}/{len(frases)}]  Di:   «{texto}»")
        accion = preguntar("  Enter = escuchar · s = saltar · q = terminar > ").strip().lower()
        if accion == "q":
            break
        if accion == "s":
            i += 1
            continue
        print("  Escuchando…")
        frase = obtener_frase(i, texto)
        if frase is None:
            print("  No se oyó voz. Se repite la frase.")
            continue
        paso = 1600  # bloques de 50 ms
        pico = max((rms(frase.audio[k : k + paso]) for k in range(0, len(frase.audio), paso)), default=0.0)
        print(
            f"  Grabación: {frase.duracion_s:.2f} s · voz: {frase.voz_s:.2f} s · pico RMS: {pico:.0f}"
        )
        r = medir_frase(frase, texto, esperado, motores, catalogo)
        for m in r.medidas:
            marca = "OK " if m.orden_ok else "MAL"
            print(f"  {marca} {m.motor:<20} {m.latencia_s:5.2f} s  «{m.texto}» → {m.obtenido}")
        if preguntar("  Enter = guardar · r = repetir esta frase > ").strip().lower() == "r":
            continue
        resultados.append(r)
        escribir(salida, cabecera, resultados, nombres)  # se guarda tras cada frase
        i += 1
    if resultados:
        escribir(salida, cabecera, resultados, nombres)
        print("\n" + "\n".join(resumen(resultados, nombres)))
        print(f"\nResultados (solo texto): {salida}")
    else:
        print("\nNo hay medidas: no se escribe ningún fichero.")
    return resultados


def microfonos() -> list[tuple[int, str]]:
    import sounddevice as sd

    apis = sd.query_hostapis()
    return [
        (i, f"{d['name']} ({apis[d['hostapi']]['name']}, {d['max_input_channels']} canales)")
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] > 0
    ]


def nombre_microfono(dispositivo) -> str:
    import sounddevice as sd

    return sd.query_devices(dispositivo, kind="input")["name"]


def elegir_microfono(opcion: str | None, preguntar: Callable[[str], str] = input):
    """None = el de Windows por defecto. «elegir» = lista y pregunta. «lista» = solo lista. Número o nombre = ese."""
    if opcion is None:
        return None
    if opcion in ("lista", "elegir"):
        import sounddevice as sd

        defecto = sd.default.device[0]
        print("Micrófonos (entrada):")
        for i, nombre in microfonos():
            print(f"  {i:3d}  {nombre}{'   ← por defecto' if i == defecto else ''}")
        if opcion == "lista":
            return "lista"
        elegido = preguntar("Número del micrófono (Enter = por defecto) > ").strip()
        return int(elegido) if elegido.isdigit() else None
    return int(opcion) if opcion.isdigit() else opcion


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--motores", default=MOTORES_POR_DEFECTO, help=f"separados por coma (por defecto {MOTORES_POR_DEFECTO})")
    p.add_argument("--max", type=int, default=None, help="número máximo de frases")
    p.add_argument("--silencio", type=float, default=SILENCIO_FIN_S, help="silencio (s) que cierra la frase")
    p.add_argument("--prerrollo", type=float, default=PRERROLLO_S, help="audio (s) que se guarda antes de la voz")
    p.add_argument(
        "--mic",
        nargs="?",
        const="elegir",
        default=None,
        help="micrófono: número o nombre; «--mic» solo = lista y pregunta; «--mic lista» = lista y sale",
    )
    p.add_argument("--salida", type=Path, default=None)
    a = p.parse_args(argv)

    dispositivo = elegir_microfono(a.mic)
    if dispositivo == "lista":
        return
    frases = leer_frases()[: a.max]
    motores, cargas = [], []
    for nombre in a.motores.split(","):
        print(f"Cargando {nombre}…", end=" ", flush=True)
        t0 = time.perf_counter()
        motores.append(crear_motor(nombre.strip()))
        cargas.append(f"{nombre.strip()} {_coma(time.perf_counter() - t0, 1)} s")
        print(cargas[-1])

    with CapturaMicrofono(dispositivo) as captura:
        print("\nCalibrando el ruido de la sala: 1 s en silencio…")
        umbral = captura.calibrar(1.0)
        print(f"Umbral de voz (RMS): {umbral:.0f}")
        detector = DetectorDeFrase(umbral, silencio_fin_s=a.silencio, prerrollo_s=a.prerrollo)
        print(f"Fin de frase tras {a.silencio:.2f} s de silencio; se guardan {a.prerrollo:.2f} s antes de la voz.")
        cabecera = [
            f"# Resultados del prototipo I-1 · {datetime.now():%Y-%m-%d %H:%M}",
            "",
            "Generado por `medir.py` con voz real. Solo texto: el audio no se guarda (REQ-24).",
            "",
            f"- Motores y tiempo de carga: {'; '.join(cargas)}.",
            f"- Micrófono: {nombre_microfono(dispositivo)}.",
            f"- Fin de frase: {_coma(a.silencio)} s de silencio (incluido en la latencia). Prerrollo: {_coma(a.prerrollo)} s. "
            f"Umbral de voz (RMS): {umbral:.0f} para empezar, {detector.umbral_fin:.0f} para seguir.",
            "- Latencia: desde el último bloque con voz hasta tener la orden del intérprete (falta el envío al robot).",
            "- vosk-flujo: Vosk recibe el audio mientras se habla; solo se cuenta el cierre del reconocimiento.",
            "- «Atenio»: es la primera palabra del texto (el intérprete lo exige, REQ-01).",
        ]
        ejecutar(frases, motores, lambda _i, _t: captura.frase(detector), a.salida or ruta_resultados(), cabecera)


if __name__ == "__main__":
    main()
