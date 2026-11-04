"""Captura de audio (componente 1 de plan.md): micrófono → una frase en memoria.

Cubre REQ-17 y REQ-24: el audio solo vive en memoria (bytes PCM); este módulo nunca escribe en el disco.
Formato: 16 kHz, mono, 16 bits con signo (el que piden Vosk y Faster-Whisper).
"""
from __future__ import annotations

import math
import queue
import time
from array import array
from dataclasses import dataclass
from typing import Callable, Iterable

FRECUENCIA_HZ = 16_000
BLOQUE_S = 0.05  # 50 ms por bloque
MUESTRAS_POR_BLOQUE = int(FRECUENCIA_HZ * BLOQUE_S)
SILENCIO_FIN_S = 0.6  # provisional: silencio que marca el fin de la frase (I-1)
MAX_FRASE_S = 8.0
ESPERA_VOZ_S = 8.0  # sin voz en este tiempo: no hay frase
UMBRAL_MINIMO = 300.0  # RMS mínimo (int16) que cuenta como voz; provisional


@dataclass(frozen=True)
class Frase:
    """Una frase capturada. `audio`: PCM int16 mono 16 kHz. `fin_voz`: hora (perf_counter) del último bloque con voz."""

    audio: bytes
    fin_voz: float
    cierre: float  # hora en que se dio la frase por terminada (fin_voz + silencio)

    @property
    def duracion_s(self) -> float:
        return len(self.audio) / 2 / FRECUENCIA_HZ


def rms(bloque: bytes) -> float:
    """Energía media (RMS) de un bloque PCM int16."""
    muestras = array("h")
    muestras.frombytes(bloque)
    if not muestras:
        return 0.0
    return math.sqrt(sum(m * m for m in muestras) / len(muestras))


class DetectorDeFrase:
    """Corta una frase de una serie de bloques: empieza con el primer bloque con voz y acaba tras `silencio_fin_s` sin voz.

    No depende del micrófono: recibe (bloque, hora) y se prueba con bloques sintéticos.
    """

    def __init__(
        self,
        umbral: float = UMBRAL_MINIMO,
        *,
        silencio_fin_s: float = SILENCIO_FIN_S,
        max_frase_s: float = MAX_FRASE_S,
        espera_voz_s: float = ESPERA_VOZ_S,
        bloque_s: float = BLOQUE_S,
        prerrollo_bloques: int = 4,
    ):
        self.umbral = umbral
        self._bloques_silencio_fin = max(1, round(silencio_fin_s / bloque_s))
        self._max_bloques = round(max_frase_s / bloque_s)
        self._espera_bloques = round(espera_voz_s / bloque_s)
        self._prerrollo = prerrollo_bloques  # bloques previos a la voz que se guardan (inicio suave)

    def cortar(self, bloques: Iterable[tuple[bytes, float]]) -> Frase | None:
        """Devuelve la frase, o None si no hubo voz en `espera_voz_s`."""
        previos: list[bytes] = []
        frase: list[bytes] = []
        en_voz = False
        silencio = 0
        esperados = 0
        fin_voz = 0.0
        hora = 0.0
        for bloque, hora in bloques:
            hay_voz = rms(bloque) >= self.umbral
            if not en_voz:
                if hay_voz:
                    en_voz = True
                    frase = previos + [bloque]
                    fin_voz = hora
                else:
                    previos = (previos + [bloque])[-self._prerrollo :] if self._prerrollo else []
                    esperados += 1
                    if esperados >= self._espera_bloques:
                        return None
                continue
            frase.append(bloque)
            if hay_voz:
                silencio = 0
                fin_voz = hora
            else:
                silencio += 1
            if silencio >= self._bloques_silencio_fin or len(frase) >= self._max_bloques:
                return Frase(b"".join(frase), fin_voz, hora)
        if en_voz:  # se acabaron los bloques en mitad de la frase
            return Frase(b"".join(frase), fin_voz, hora)
        return None


def calibrar_umbral(bloques: Iterable[bytes], factor: float = 3.0) -> float:
    """Umbral de voz a partir del ruido de la sala: `factor` × RMS medio, nunca menos que UMBRAL_MINIMO."""
    valores = [rms(b) for b in bloques]
    base = sum(valores) / len(valores) if valores else 0.0
    return max(UMBRAL_MINIMO, base * factor)


class CapturaMicrofono:
    """Lee el micrófono con `sounddevice` y entrega frases en memoria (REQ-17, REQ-24).

    `sounddevice` se importa al abrir el micrófono, así las pruebas no lo necesitan.
    """

    def __init__(self, dispositivo: int | str | None = None, *, reloj: Callable[[], float] = time.perf_counter):
        self._dispositivo = dispositivo
        self._reloj = reloj
        self._cola: queue.Queue[tuple[bytes, float]] = queue.Queue()
        self._flujo = None

    def abrir(self) -> None:
        import sounddevice as sd  # dependencia solo del micrófono real

        def al_recibir(datos, _frames, _tiempo, _estado):
            self._cola.put((bytes(datos), self._reloj()))

        self._flujo = sd.RawInputStream(
            samplerate=FRECUENCIA_HZ,
            blocksize=MUESTRAS_POR_BLOQUE,
            channels=1,
            dtype="int16",
            device=self._dispositivo,
            callback=al_recibir,
        )
        self._flujo.start()

    def cerrar(self) -> None:
        if self._flujo is not None:
            self._flujo.stop()
            self._flujo.close()
            self._flujo = None

    def __enter__(self) -> "CapturaMicrofono":
        self.abrir()
        return self

    def __exit__(self, *_exc) -> None:
        self.cerrar()

    def vaciar(self) -> None:
        """Descarta el audio que llegó antes (por ejemplo mientras se transcribía)."""
        while not self._cola.empty():
            self._cola.get_nowait()

    def bloques(self) -> Iterable[tuple[bytes, float]]:
        while True:
            yield self._cola.get()

    def calibrar(self, segundos: float = 1.0) -> float:
        self.vaciar()
        n = max(1, round(segundos / BLOQUE_S))
        return calibrar_umbral(self._cola.get()[0] for _ in range(n))

    def frase(self, detector: DetectorDeFrase) -> Frase | None:
        self.vaciar()
        return detector.cortar(self.bloques())
