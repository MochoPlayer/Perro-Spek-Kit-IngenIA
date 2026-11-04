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

    def transcribir(self, audio: bytes) -> str:
        if self._gramatica:
            rec = self._vosk.KaldiRecognizer(self._modelo, FRECUENCIA_HZ, self._gramatica)
        else:
            rec = self._vosk.KaldiRecognizer(self._modelo, FRECUENCIA_HZ)
        rec.AcceptWaveform(audio)
        return json.loads(rec.FinalResult()).get("text", "").strip()


class TranscriptorWhisper:
    """Faster-Whisper en CPU (int8). `tamano`: "tiny" o "base". `pista`: texto inicial opcional (por ejemplo «Atenio»)."""

    def __init__(
        self,
        tamano: str = "base",
        *,
        carpeta_modelos: str | Path | None = None,
        idioma: str = "es",
        pista: str | None = None,
        nombre: str | None = None,
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
