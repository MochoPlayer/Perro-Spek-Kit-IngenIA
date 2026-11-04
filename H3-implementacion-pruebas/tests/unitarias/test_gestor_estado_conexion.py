"""T060: el gestor publica el estado de conexión como evento para la interfaz (REQ-19, REQ-25, D-13).

Sin robot: robot y reloj simulados (REQ-26).
"""
from __future__ import annotations

import pytest

from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import AVISO_NO_CONECTADO, TipoEvento
from atenio.gestor_acciones import ESTADO_CONECTADO, ESTADO_DESCONECTADO, GestorAcciones
from atenio.modelos import Interpretacion, Orden, Paso, TipoInterpretacion

SIENTATE = Orden("REQ-02", ("siéntate",), (Paso("ksit", 2.0),))


class EnlaceQueNoConecta(EnlaceSimulado):
    def conectar(self) -> bool:
        return False


def estados(gestor: GestorAcciones) -> list[str]:
    return gestor.eventos.textos(TipoEvento.ESTADO_CONEXION)


def test_crear_el_gestor_no_publica_nada(reloj):
    gestor = GestorAcciones(EnlaceSimulado(reloj, conectado=False), reloj)
    assert estados(gestor) == []


def test_conectar_publica_conectado(reloj):
    robot = EnlaceSimulado(reloj, conectado=False)
    gestor = GestorAcciones(robot, reloj)
    assert gestor.conectar() is True
    assert robot.conectado
    assert estados(gestor) == [ESTADO_CONECTADO]
    assert gestor.eventos.avisos == []


def test_si_no_conecta_publica_desconectado_y_avisa(reloj):
    gestor = GestorAcciones(EnlaceQueNoConecta(reloj, conectado=False), reloj)
    assert gestor.conectar() is False
    assert estados(gestor) == [ESTADO_DESCONECTADO]
    assert gestor.eventos.avisos == [AVISO_NO_CONECTADO]


@pytest.mark.parametrize("conectado, texto", [(True, ESTADO_CONECTADO), (False, ESTADO_DESCONECTADO)])
def test_publicar_estado_actual_para_la_interfaz(reloj, conectado, texto):
    gestor = GestorAcciones(EnlaceSimulado(reloj, conectado=conectado), reloj)
    gestor.publicar_estado_conexion()
    assert estados(gestor) == [texto]


def test_tick_publica_la_desconexion_del_enlace_una_sola_vez(reloj):
    """El cable se suelta sin que falle ningún envío: el enlace pasa a desconectado y el gestor lo cuenta."""
    robot = EnlaceSimulado(reloj)
    gestor = GestorAcciones(robot, reloj)
    gestor.tick()
    assert estados(gestor) == []
    robot.simular_sin_conexion()
    gestor.tick()
    gestor.tick()
    assert estados(gestor) == [ESTADO_DESCONECTADO]


def test_tick_publica_la_reconexion(reloj):
    robot = EnlaceSimulado(reloj, conectado=False)
    gestor = GestorAcciones(robot, reloj)
    robot.conectar()
    gestor.tick()
    assert estados(gestor) == [ESTADO_CONECTADO]


def test_fallo_de_envio_publica_desconectado_y_tick_no_lo_repite(reloj):
    robot = EnlaceSimulado(reloj)
    gestor = GestorAcciones(robot, reloj)
    robot.fallo_envio = True
    gestor.recibir(Interpretacion(TipoInterpretacion.ORDENES, (SIENTATE,)))
    gestor.tick()
    assert estados(gestor) == [ESTADO_DESCONECTADO]


def test_la_interfaz_recibe_el_estado_por_suscripcion(reloj):
    recibidos = []
    gestor = GestorAcciones(EnlaceSimulado(reloj, conectado=False), reloj)
    gestor.eventos.suscribir(lambda e: recibidos.append((e.tipo, e.texto)))
    gestor.conectar()
    assert recibidos == [(TipoEvento.ESTADO_CONEXION, ESTADO_CONECTADO)]
