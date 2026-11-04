"""REQ-24 / SC-008 (parte automática, T049): capturar y transcribir no escribe ningún fichero.

Se vigilan dos cosas mientras corre la cadena micrófono falso → detector → adaptador falso → intérprete:
1) ninguna apertura de fichero en modo escritura; 2) ningún fichero nuevo en la carpeta de trabajo ni en H3.
"""
from __future__ import annotations

import builtins
import io
import os
from pathlib import Path

import pytest

from atenio.audio import CapturaMicrofono, DetectorDeFrase
from atenio.interprete import Interprete
from atenio.transcripcion import TranscriptorFalso
from test_audio import microfono_falso, silencio, tono  # noqa: F401 (fixture)

CARPETA_H3 = Path(__file__).resolve().parents[2]


def ficheros(carpeta: Path) -> set[Path]:
    return {p for p in carpeta.rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}


@pytest.fixture
def escrituras(monkeypatch):
    """Registra toda apertura de fichero que pueda escribir (open, io.open, os.open)."""
    vistas: list[str] = []
    abrir, abrir_os = builtins.open, os.open

    def open_vigilado(fichero, mode="r", *a, **k):
        if any(c in mode for c in "wax+"):
            vistas.append(str(fichero))
        return abrir(fichero, mode, *a, **k)

    def os_open_vigilado(ruta, flags, *a, **k):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
            vistas.append(str(ruta))
        return abrir_os(ruta, flags, *a, **k)

    monkeypatch.setattr(builtins, "open", open_vigilado)
    monkeypatch.setattr(io, "open", open_vigilado)
    monkeypatch.setattr(os, "open", os_open_vigilado)
    return vistas


def test_una_sesion_no_deja_ficheros_de_audio(tmp_path, monkeypatch, microfono_falso, escrituras, catalogo, reloj):
    monkeypatch.chdir(tmp_path)
    antes_h3, antes_tmp = ficheros(CARPETA_H3), ficheros(tmp_path)

    microfono_falso.bloques = ([tono()] * 20 + [silencio()] * 20) * 3
    transcriptor = TranscriptorFalso(["Atenio, siéntate", "Atenio, camina", "Atenio, para"])
    interprete = Interprete(catalogo, reloj=reloj)
    detector = DetectorDeFrase(silencio_fin_s=0.5, prerrollo_bloques=0)
    resultados = []
    with CapturaMicrofono() as captura:
        bloques = captura.bloques()
        for _ in range(3):
            frase = detector.cortar(next(bloques) for _ in range(40))
            assert frase is not None
            resultados.append(interprete.interpretar(transcriptor.transcribir(frase.audio)))

    assert [r.ordenes[0].id for r in resultados] == ["REQ-02", "REQ-04", "REQ-07"]
    assert escrituras == []
    assert ficheros(tmp_path) == antes_tmp
    assert ficheros(CARPETA_H3) == antes_h3


def test_el_codigo_de_captura_no_usa_ficheros_de_audio():
    """Inspección automática (complementa la revisión de T042): ni wave, ni soundfile, ni escritura a disco."""
    for nombre in ("audio.py", "transcripcion.py"):
        fuente = (CARPETA_H3 / "src" / "atenio" / nombre).read_text(encoding="utf-8")
        for prohibido in ("import wave", "soundfile", "scipy.io", "write_bytes", ".wav", "tempfile", "open("):
            assert prohibido not in fuente, f"{nombre} contiene «{prohibido}»"
