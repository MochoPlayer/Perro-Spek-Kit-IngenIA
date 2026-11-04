"""Captura de audio (componente 1 de plan.md): micrófono → una frase en memoria.

Cubre REQ-17 y REQ-24: el audio solo vive en memoria (bytes PCM); este módulo nunca escribe en el disco.
Formato: 16 kHz, mono, 16 bits con signo (el que piden Vosk y Faster-Whisper).
`MedidorNivel` guarda solo el nivel (RMS) de cada bloque, para dibujar la onda en la interfaz: números, nunca audio.
"""
from __future__ import annotations

import math
import queue
import threading
import time
from array import array
from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable

FRECUENCIA_HZ = 16_000
BLOQUE_S = 0.05  # 50 ms por bloque
MUESTRAS_POR_BLOQUE = int(FRECUENCIA_HZ * BLOQUE_S)
SILENCIO_FIN_S = 0.9  # provisional: silencio que marca el fin de la frase (I-1; con 0,6 s se cortaba «siéntate»)
PRERROLLO_S = 0.3  # audio que se guarda antes del primer bloque con voz (consonantes suaves del inicio)
FACTOR_UMBRAL_FIN = 0.6  # una vez dentro de la frase, basta este factor × umbral para seguir contando como voz
MAX_FRASE_S = 8.0
ESPERA_VOZ_S = 8.0  # sin voz en este tiempo: no hay frase
UMBRAL_MINIMO = 300.0  # RMS mínimo (int16) que cuenta como voz; provisional


@dataclass(frozen=True)
class Frase:
    """Una frase capturada. `audio`: PCM int16 mono 16 kHz. Horas en segundos (perf_counter)."""

    audio: bytes
    fin_voz: float  # hora del último bloque con voz
    cierre: float  # hora en que se dio la frase por terminada (fin_voz + silencio)
    inicio_voz: float | None = None  # hora del primer bloque con voz

    @property
    def duracion_s(self) -> float:
        """Duración de toda la grabación (prerrollo + voz + silencio final)."""
        return len(self.audio) / 2 / FRECUENCIA_HZ

    @property
    def voz_s(self) -> float:
        """Duración de la parte con voz (del primer al último bloque con voz, ambos incluidos)."""
        if self.inicio_voz is None:
            return self.duracion_s
        return self.fin_voz - self.inicio_voz + BLOQUE_S


def rms(bloque: bytes) -> float:
    """Energía media (RMS) de un bloque PCM int16."""
    muestras = array("h")
    muestras.frombytes(bloque)
    if not muestras:
        return 0.0
    return math.sqrt(sum(m * m for m in muestras) / len(muestras))


class DetectorDeFrase:
    """Corta una frase de una serie de bloques: empieza con el primer bloque con voz y acaba tras `silencio_fin_s` sin voz.

    Para empezar hace falta `umbral`; para seguir en la frase basta `umbral × factor_umbral_fin`, así las
    sílabas flojas del final («-tate») no la cortan. No depende del micrófono: recibe (bloque, hora).
    """

    def __init__(
        self,
        umbral: float = UMBRAL_MINIMO,
        *,
        silencio_fin_s: float = SILENCIO_FIN_S,
        prerrollo_s: float = PRERROLLO_S,
        factor_umbral_fin: float = FACTOR_UMBRAL_FIN,
        max_frase_s: float = MAX_FRASE_S,
        espera_voz_s: float = ESPERA_VOZ_S,
        bloque_s: float = BLOQUE_S,
    ):
        self.umbral = umbral
        self.umbral_fin = umbral * factor_umbral_fin
        self.silencio_fin_s = silencio_fin_s
        self.prerrollo_s = prerrollo_s
        self._bloques_silencio_fin = max(1, round(silencio_fin_s / bloque_s))
        self._max_bloques = round(max_frase_s / bloque_s)
        self._espera_bloques = round(espera_voz_s / bloque_s)
        self._prerrollo = max(0, round(prerrollo_s / bloque_s))

    def cortar(self, bloques: Iterable[tuple[bytes, float]]) -> Frase | None:
        """Devuelve la frase, o None si no hubo voz en `espera_voz_s`."""
        previos: list[bytes] = []
        frase: list[bytes] = []
        en_voz = False
        silencio = 0
        esperados = 0
        inicio_voz = fin_voz = hora = 0.0
        for bloque, hora in bloques:
            energia = rms(bloque)
            if not en_voz:
                if energia >= self.umbral:
                    en_voz = True
                    frase = previos + [bloque]
                    inicio_voz = fin_voz = hora
                else:
                    previos = (previos + [bloque])[-self._prerrollo :] if self._prerrollo else []
                    esperados += 1
                    if esperados >= self._espera_bloques:
                        return None
                continue
            frase.append(bloque)
            if energia >= self.umbral_fin:
                silencio = 0
                fin_voz = hora
            else:
                silencio += 1
            if silencio >= self._bloques_silencio_fin or len(frase) >= self._max_bloques:
                return Frase(b"".join(frase), fin_voz, hora, inicio_voz)
        if en_voz:  # se acabaron los bloques en mitad de la frase
            return Frase(b"".join(frase), fin_voz, hora, inicio_voz)
        return None


def calibrar_umbral(bloques: Iterable[bytes], factor: float = 3.0) -> float:
    """Umbral de voz a partir del ruido de la sala: `factor` × RMS medio, nunca menos que UMBRAL_MINIMO."""
    valores = [rms(b) for b in bloques]
    base = sum(valores) / len(valores) if valores else 0.0
    return max(UMBRAL_MINIMO, base * factor)


class MedidorNivel:
    """Los últimos niveles (RMS) del micrófono, para la onda de la interfaz. Solo números en memoria (REQ-24).

    `desde(n)` devuelve los niveles con número de orden mayor o igual que `n` y el total anotado hasta ahora.
    `umbral` es el umbral de voz calibrado (None mientras se calibra).
    """

    def __init__(self, maximo: int = 200) -> None:
        self._valores: deque[float] = deque(maxlen=maximo)
        self._total = 0
        self._cerrojo = threading.Lock()
        self.umbral: float | None = None

    def anotar(self, nivel: float) -> None:
        with self._cerrojo:
            self._valores.append(round(float(nivel), 1))
            self._total += 1

    def desde(self, n: int) -> tuple[list[float], int]:
        with self._cerrojo:
            nuevos = max(0, min(self._total - max(0, n), len(self._valores)))
            valores = list(self._valores)[len(self._valores) - nuevos:] if nuevos else []
            return valores, self._total


class CapturaMicrofono:
    """Lee el micrófono con `sounddevice` y entrega frases en memoria (REQ-17, REQ-24).

    `sounddevice` se importa al abrir el micrófono, así las pruebas no lo necesitan.
    """

    def __init__(
        self,
        dispositivo: int | str | None = None,
        *,
        reloj: Callable[[], float] = time.perf_counter,
        medidor: MedidorNivel | None = None,
    ):
        self._dispositivo = dispositivo
        self.medidor = medidor  # si hay, recibe el RMS de cada bloque en cuanto llega (la onda no espera a la transcripción)
        self._reloj = reloj
        self._cola: queue.Queue[tuple[bytes, float]] = queue.Queue()
        self._flujo = None

    def abrir(self) -> None:
        import sounddevice as sd  # dependencia solo del micrófono real

        def al_recibir(datos, _frames, _tiempo, _estado):
            bloque = bytes(datos)
            self._cola.put((bloque, self._reloj()))
            if self.medidor is not None:
                self.medidor.anotar(rms(bloque))

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

    def bloques(self, parar: threading.Event | None = None) -> Iterable[tuple[bytes, float]]:
        """Bloques (audio, hora) según llegan. Con `parar`, la serie acaba poco después de activarlo (escucha continua)."""
        if parar is None:
            while True:
                yield self._cola.get()
        while not parar.is_set():
            try:
                yield self._cola.get(timeout=0.1)
            except queue.Empty:
                continue

    def calibrar(self, segundos: float = 1.0) -> float:
        self.vaciar()
        n = max(1, round(segundos / BLOQUE_S))
        return calibrar_umbral(self._cola.get()[0] for _ in range(n))

    def frase(self, detector: DetectorDeFrase) -> Frase | None:
        self.vaciar()
        return detector.cortar(self.bloques())
