"""Adaptador de transcripción (componente 2 de plan.md, D-02): audio en memoria → texto.

Una sola interfaz (`Transcriptor`) con una versión por motor (Vosk, Faster-Whisper) y una falsa para las pruebas.
Cubre REQ-18 (el motor es un módulo existente) y REQ-24 (el audio se pasa en memoria; nada se escribe en el disco).
El motor definitivo lo elige el equipo (P-01) con el prototipo I-1 (prototipos/motor-voz/).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Protocol

from atenio.audio import FRECUENCIA_HZ


class Transcriptor(Protocol):
    """Interfaz única: PCM int16 mono 16 kHz → texto ("" si no se reconoce nada)."""

    nombre: str

    def transcribir(self, audio: bytes) -> str: ...


class TranscriptorFalso:
    """Para las pruebas: devuelve los textos dados, uno por llamada; "" cuando se acaban."""

    def __init__(self, textos: Iterable[str] = (), nombre: str = "falso"):
        self.nombre = nombre
        self._textos = list(textos)
        self.recibido: list[int] = []  # bytes de audio recibidos en cada llamada

    def transcribir(self, audio: bytes) -> str:
        self.recibido.append(len(audio))
        return self._textos.pop(0) if self._textos else ""


class TranscriptorVosk:
    """Vosk (Kaldi) con un modelo local. `gramatica`: lista opcional de frases/palabras permitidas."""

    def __init__(self, ruta_modelo: str | Path, *, gramatica: list[str] | None = None, nombre: str = "vosk"):
        import vosk  # dependencia del motor; las pruebas no la necesitan

        vosk.SetLogLevel(-1)
        self.nombre = nombre
        self._vosk = vosk
        self._modelo = vosk.Model(str(ruta_modelo))
        self._gramatica = json.dumps(gramatica, ensure_ascii=False) if gramatica else None

    def _reconocedor(self):
        if self._gramatica:
            return self._vosk.KaldiRecognizer(self._modelo, FRECUENCIA_HZ, self._gramatica)
        return self._vosk.KaldiRecognizer(self._modelo, FRECUENCIA_HZ)

    def transcribir(self, audio: bytes) -> str:
        flujo = self.flujo()
        flujo.aceptar(audio)
        return flujo.terminar()

    def flujo(self) -> "FlujoVosk":
        """Reconocimiento en flujo: se le pasan los bloques mientras la persona habla."""
        return FlujoVosk(self._reconocedor())


class FlujoVosk:
    def __init__(self, reconocedor):
        self._rec = reconocedor

    def aceptar(self, bloque: bytes) -> None:
        self._rec.AcceptWaveform(bloque)

    def terminar(self) -> str:
        return json.loads(self._rec.FinalResult()).get("text", "").strip()


class TranscriptorWhisper:
    """Faster-Whisper en CPU (int8). `tamano`: "tiny" o "base". `pista`: texto inicial opcional (por ejemplo «Atenio»).
    `solo_local`: no baja nada de la red (la escucha del programa lo usa)."""

    def __init__(
        self,
        tamano: str = "base",
        *,
        carpeta_modelos: str | Path | None = None,
        idioma: str = "es",
        pista: str | None = None,
        nombre: str | None = None,
        solo_local: bool = False,
    ):
        from faster_whisper import WhisperModel  # dependencia del motor

        self.nombre = nombre or f"whisper-{tamano}"
        self._idioma = idioma
        self._pista = pista
        self._modelo = WhisperModel(
            tamano,
            device="cpu",
            compute_type="int8",
            download_root=str(carpeta_modelos) if carpeta_modelos else None,
            local_files_only=solo_local,  # True: no usa la red; el modelo debe estar ya bajado (REQ-24)
        )

    def transcribir(self, audio: bytes) -> str:
        import numpy as np

        muestras = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
        segmentos, _info = self._modelo.transcribe(
            muestras,
            language=self._idioma,
            beam_size=1,
            initial_prompt=self._pista,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segmentos).strip()
