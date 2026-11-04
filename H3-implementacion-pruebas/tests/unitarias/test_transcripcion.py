"""Pruebas del adaptador de transcripción con el motor falso (T049; REQ-18). Sin micrófono ni modelos."""
from __future__ import annotations

from atenio.interprete import Interprete
from atenio.modelos import TipoInterpretacion
from atenio.transcripcion import Transcriptor, TranscriptorFalso


def test_el_falso_devuelve_los_textos_en_orden_y_luego_vacio():
    t = TranscriptorFalso(["perro siéntate", "perro camina"])
    assert t.transcribir(b"\x00" * 10) == "perro siéntate"
    assert t.transcribir(b"\x00" * 20) == "perro camina"
    assert t.transcribir(b"\x00" * 30) == ""
    assert t.recibido == [10, 20, 30]


def test_el_falso_cumple_la_interfaz():
    t: Transcriptor = TranscriptorFalso(nombre="prueba")
    assert t.nombre == "prueba"
    assert isinstance(t.transcribir(b""), str)


def test_texto_del_adaptador_llega_al_interprete(catalogo, reloj):
    """La salida del adaptador es la entrada del intérprete (REQ-18: motor externo + intérprete propio)."""
    t = TranscriptorFalso(["Perro, siéntate", ""])
    interprete = Interprete(catalogo, reloj=reloj)
    r = interprete.interpretar(t.transcribir(b"\x00" * 3200))
    assert r.tipo is TipoInterpretacion.ORDENES
    assert [o.id for o in r.ordenes] == ["REQ-02"]
    assert interprete.interpretar(t.transcribir(b"")).tipo is TipoInterpretacion.IGNORADA


def test_los_motores_reales_no_se_importan_al_cargar_el_adaptador():
    """Las pruebas corren sin vosk ni faster-whisper: el módulo solo los importa al crear un motor real."""
    import importlib
    import sys

    import atenio.transcripcion as modulo

    importlib.reload(modulo)
    fuente = open(modulo.__file__, encoding="utf-8").read()
    cabecera = fuente.split("class ")[0]
    assert "import vosk" not in cabecera and "faster_whisper" not in cabecera.replace("Faster-Whisper", "")
    assert "atenio.transcripcion" in sys.modules
