"""Escucha continua (componentes 1 y 2 de plan.md; T051, base de T057): micrófono → frase → texto → `al_oir(texto)`.

Un hilo abre el micrófono, calibra el ruido, corta frases y las transcribe. El audio solo vive en memoria (REQ-17, REQ-24).
El motor se elige en `datos/ajustes.json`, sección «voz» (provisional: P-01 pendiente del equipo).
"""
from __future__ import annotations

import importlib.util
import logging
import threading
from pathlib import Path
from typing import Callable, Iterable, Protocol

from atenio.audio import (
    BLOQUE_S,
    PRERROLLO_S,
    SILENCIO_FIN_S,
    CapturaMicrofono,
    DetectorDeFrase,
    MedidorNivel,
    calibrar_umbral,
)
from atenio.transcripcion import Transcriptor, TranscriptorFalso

registro = logging.getLogger(__name__)

CARPETA_H3 = Path(__file__).resolve().parents[2]
MOTORES = ("vosk", "whisper-tiny", "whisper-base", "falso")

# Valores del prototipo I-1 (prototipos/motor-voz/README.md). Provisionales: P-01.
VOZ_POR_DEFECTO = {
    "motor": "vosk",
    "micro": None,
    "silencio_s": SILENCIO_FIN_S,
    "prerrollo_s": PRERROLLO_S,
    "calibrar_s": 1.0,
    "pista": "Perro",
    "carpeta_modelos": "prototipos/motor-voz/modelos",
    "modelo_vosk": "vosk-model-small-es-0.42",
    "frases": [],  # solo para el motor «falso»
}

COMO_INSTALAR = "py -3.12 -m pip install -r H3-implementacion-pruebas/requirements-voz.txt"


class ErrorDeVoz(RuntimeError):
    """Falta una biblioteca o un modelo de voz, o el ajuste no es válido. El mensaje dice qué hacer."""


class Escucha(Protocol):
    activa: bool

    def iniciar(self, al_oir: Callable[[str], None]) -> None: ...

    def parar(self) -> None: ...


class _Hilo:
    """Parte común: hilo propio, `activa`, `parar()` y `al_oir` protegido (un fallo del receptor no para la escucha)."""

    def __init__(self) -> None:
        self.activa = False
        self.error: BaseException | None = None  # último fallo del hilo (por ejemplo, el micrófono no abre)
        self.nivel: MedidorNivel | None = None  # niveles del micrófono para la onda; None sin micrófono
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None

    def iniciar(self, al_oir: Callable[[str], None]) -> None:
        if self.activa:
            return
        self._parar.clear()
        self.error = None
        self.activa = True
        self._hilo = threading.Thread(target=self._correr, args=(al_oir,), name=type(self).__name__, daemon=True)
        self._hilo.start()

    def parar(self, espera_s: float = 2.0) -> None:
        self._parar.set()
        if self._hilo is not None and self._hilo is not threading.current_thread():
            self._hilo.join(espera_s)
        self.activa = False

    def esperar(self, espera_s: float | None = None) -> None:
        """Espera a que el hilo acabe solo (útil en pruebas con `EscuchaFalsa`)."""
        if self._hilo is not None:
            self._hilo.join(espera_s)

    def _correr(self, al_oir: Callable[[str], None]) -> None:
        try:
            self._bucle(al_oir)
        except Exception as e:  # el hilo no debe morir en silencio
            self.error = e
            registro.error("La escucha se ha parado: %s", e)
        finally:
            self.activa = False

    def _entregar(self, al_oir: Callable[[str], None], texto: str) -> None:
        texto = (texto or "").strip()
        if not texto or self._parar.is_set():
            return
        try:
            al_oir(texto)
        except Exception:
            registro.exception("Fallo al pasar el texto reconocido «%s»", texto)

    def _bucle(self, al_oir: Callable[[str], None]) -> None:
        raise NotImplementedError


class EscuchaFalsa(_Hilo):
    """Para pruebas y demostraciones sin micrófono: entrega las frases dadas en orden y acaba. Texto vacío no se entrega."""

    def __init__(self, frases: Iterable[str] = (), *, pausa_s: float = 0.0):
        super().__init__()
        self.frases = list(frases)
        self.pausa_s = pausa_s

    def _bucle(self, al_oir: Callable[[str], None]) -> None:
        for frase in self.frases:
            parada = self._parar.wait(self.pausa_s) if self.pausa_s else self._parar.is_set()
            if parada:
                return
            self._entregar(al_oir, frase)


class EscuchaMicrofono(_Hilo):
    """Escucha real: `CapturaMicrofono` → calibrar → `DetectorDeFrase` → `Transcriptor` → `al_oir(texto)`."""

    def __init__(
        self,
        transcriptor: Transcriptor,
        *,
        micro: int | str | None = None,
        silencio_s: float = SILENCIO_FIN_S,
        prerrollo_s: float = PRERROLLO_S,
        calibrar_s: float = 1.0,
        captura: CapturaMicrofono | None = None,
    ):
        super().__init__()
        self.transcriptor = transcriptor
        self.umbral: float | None = None  # se fija al calibrar
        self.nivel = MedidorNivel()
        self._captura = captura or CapturaMicrofono(micro)
        if self._captura.medidor is None:
            self._captura.medidor = self.nivel
        self._silencio_s = silencio_s
        self._prerrollo_s = prerrollo_s
        self._calibrar_s = calibrar_s

    def _bucle(self, al_oir: Callable[[str], None]) -> None:
        self.nivel.umbral = None  # se vuelve a calibrar en cada encendido
        with self._captura as captura:
            bloques = iter(captura.bloques(self._parar))
            n = max(0, round(self._calibrar_s / BLOQUE_S))
            self.umbral = calibrar_umbral(b for b, _hora in _primeros(bloques, n))
            self.nivel.umbral = self.umbral
            registro.info("Escucha calibrada: umbral de voz (RMS) %.0f", self.umbral)
            detector = DetectorDeFrase(self.umbral, silencio_fin_s=self._silencio_s, prerrollo_s=self._prerrollo_s)
            while not self._parar.is_set():
                frase = detector.cortar(bloques)  # None: 8 s sin voz; se sigue escuchando
                if frase is None or self._parar.is_set():
                    continue
                self._entregar(al_oir, self.transcriptor.transcribir(frase.audio))


def _primeros(bloques, n: int):
    for _ in range(n):
        try:
            yield next(bloques)
        except StopIteration:
            return


def _seccion_voz(ajustes) -> dict:
    """Acepta un `Ajustes` (usa `.voz`), un dict con la sección «voz» o None (lee datos/ajustes.json)."""
    if ajustes is None:
        from atenio.ajustes import cargar_ajustes

        ajustes = cargar_ajustes()
    voz = getattr(ajustes, "voz", ajustes)
    return {**VOZ_POR_DEFECTO, **(voz or {})}


def _exigir_biblioteca(modulo: str, para: str) -> None:
    if importlib.util.find_spec(modulo) is None:
        raise ErrorDeVoz(f"Falta la biblioteca «{modulo}» ({para}). Instálala con:\n  {COMO_INSTALAR}")


def _carpeta_modelos(voz: dict) -> Path:
    carpeta = Path(voz["carpeta_modelos"])
    return carpeta if carpeta.is_absolute() else CARPETA_H3 / carpeta


def crear_transcriptor(voz: dict) -> Transcriptor:
    """El transcriptor del motor de la sección «voz». Comprueba antes la biblioteca y el modelo (error claro en español)."""
    motor = voz["motor"]
    if motor == "falso":
        return TranscriptorFalso(voz.get("frases", []))
    if motor not in MOTORES:
        raise ErrorDeVoz(f"Motor de voz «{motor}» desconocido en ajustes.json (voz.motor). Valores válidos: {', '.join(MOTORES)}.")
    carpeta = _carpeta_modelos(voz)
    if motor == "vosk":
        _exigir_biblioteca("vosk", "motor Vosk")
        ruta = carpeta / voz["modelo_vosk"]
        if not ruta.is_dir():
            raise ErrorDeVoz(
                f"No está el modelo de Vosk en {ruta}.\n"
                f"Bájalo de https://alphacephei.com/vosk/models («{voz['modelo_vosk']}») y descomprímelo en {carpeta}."
            )
        from atenio.transcripcion import TranscriptorVosk

        return TranscriptorVosk(ruta)
    tamano = motor.split("-")[1]
    _exigir_biblioteca("faster_whisper", "motor Faster-Whisper")
    if not (carpeta / f"models--Systran--faster-whisper-{tamano}").is_dir():
        raise ErrorDeVoz(
            f"No está el modelo Faster-Whisper «{tamano}» en {carpeta}.\n"
            "Bájalo una vez (necesita red), desde H3-implementacion-pruebas/:\n"
            f"  py -3.12 -c \"from faster_whisper import WhisperModel; WhisperModel('{tamano}', device='cpu', "
            f"compute_type='int8', download_root=r'{carpeta}')\""
        )
    from atenio.transcripcion import TranscriptorWhisper

    return TranscriptorWhisper(tamano, carpeta_modelos=carpeta, pista=voz.get("pista") or None, solo_local=True)


def crear_escucha(ajustes=None) -> Escucha:
    """Escucha según la sección «voz» de ajustes.json. Con `motor: falso` devuelve una `EscuchaFalsa` (sin micrófono).

    Carga el modelo aquí (puede tardar unos segundos) para dar el error antes de abrir el micrófono.
    """
    voz = _seccion_voz(ajustes)
    if voz["motor"] == "falso":
        return EscuchaFalsa(voz.get("frases", []))
    _exigir_biblioteca("sounddevice", "micrófono")
    return EscuchaMicrofono(
        crear_transcriptor(voz),
        micro=voz["micro"],
        silencio_s=float(voz["silencio_s"]),
        prerrollo_s=float(voz["prerrollo_s"]),
        calibrar_s=float(voz["calibrar_s"]),
    )
