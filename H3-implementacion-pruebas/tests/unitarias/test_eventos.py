"""Pruebas de eventos.py (T009): los cuatro tipos de evento hacia la interfaz y los textos de aviso.

Cubre REQ-19 (parte de eventos), D-07 y D-14 (avisos solo en pantalla, sin pitido `b`).
"""
from __future__ import annotations

import pytest

from atenio import eventos as ev
from atenio.eventos import Evento, Eventos, TipoEvento
from atenio.interprete import AVISO_NO_DISPONIBLE, AVISO_NO_ENTENDIDA


def test_hay_cuatro_tipos_de_evento():
    """plan.md, «Modelo de datos»: texto reconocido, orden interpretada, estado de conexión, aviso."""
    assert {t.value for t in TipoEvento} == {"texto_reconocido", "orden_interpretada", "estado_conexion", "aviso"}


def test_un_receptor_recibe_los_cuatro_tipos_en_orden():
    eventos = Eventos()
    recibidos: list[Evento] = []
    eventos.suscribir(recibidos.append)
    for tipo in TipoEvento:
        eventos.publicar(tipo, tipo.value)
    assert [e.tipo for e in recibidos] == list(TipoEvento)
    assert recibidos == eventos.lista


def test_varios_receptores_reciben_lo_mismo():
    eventos = Eventos()
    a: list[Evento] = []
    b: list[Evento] = []
    eventos.suscribir(a.append)
    eventos.suscribir(b.append)
    eventos.publicar(TipoEvento.AVISO, "x")
    assert a == b == [Evento(TipoEvento.AVISO, "x")]


def test_consultas_por_tipo():
    eventos = Eventos()
    eventos.publicar(TipoEvento.TEXTO_RECONOCIDO, "Perro, siéntate")
    eventos.publicar(TipoEvento.AVISO, "uno")
    eventos.publicar(TipoEvento.ORDEN_INTERPRETADA, "REQ-02")
    eventos.publicar(TipoEvento.AVISO, "dos")
    assert eventos.textos(TipoEvento.ORDEN_INTERPRETADA) == ["REQ-02"]
    assert eventos.avisos == ["uno", "dos"]


def test_el_evento_no_se_puede_cambiar():
    e = Evento(TipoEvento.AVISO, "x")
    with pytest.raises(AttributeError):
        e.texto = "y"  # type: ignore[misc]


def test_textos_exactos_de_spec():
    """REQ-12, REQ-25, REQ-30: textos fijados en spec.md."""
    assert AVISO_NO_ENTENDIDA == "no se ha entendido bien"
    assert ev.AVISO_NO_CONECTADO == "robot no conectado"
    assert ev.AVISO_PARADA_ACTIVA == "parada de emergencia activa"


@pytest.mark.parametrize("texto", [
    AVISO_NO_ENTENDIDA, AVISO_NO_DISPONIBLE, ev.AVISO_NO_CONECTADO, ev.AVISO_PARADA_ACTIVA,
    ev.AVISO_BATERIA_BAJA, ev.AVISO_CONEXION_PERDIDA,
])
def test_ningun_aviso_es_el_pitido_b(texto):
    """D-14: los avisos son texto en pantalla, nunca el comando `b` del robot."""
    assert texto.strip() and texto.strip().split()[0] != "b"
