"""T055: un receptor de eventos (en lugar de la interfaz) recibe texto, orden, estado de conexión y aviso.

Cubre REQ-19 y el hallazgo U2 de coherencia.md (estado de conexión también al conectar, T060). Sin abrir la interfaz.
"""
from __future__ import annotations

from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import AVISO_CONEXION_PERDIDA, AVISO_NO_CONECTADO, Evento, TipoEvento
from atenio.interprete import AVISO_NO_ENTENDIDA
from atenio.principal import Sistema
from atenio.reloj import RelojSimulado


def montar(catalogo, *, conectado: bool = True) -> tuple[Sistema, EnlaceSimulado, list[Evento]]:
    reloj = RelojSimulado()
    robot = EnlaceSimulado(reloj, conectado=conectado)
    robot.conectar = lambda: robot.conectado  # type: ignore[method-assign]  # no se «arregla» solo al arrancar
    sistema = Sistema(robot, reloj, catalogo=catalogo)
    recibidos: list[Evento] = []
    sistema.suscribir(recibidos.append)
    sistema.arrancar(con_bucle=False)
    return sistema, robot, recibidos


def de_tipo(recibidos: list[Evento], tipo: TipoEvento) -> list[str]:
    return [e.texto for e in recibidos if e.tipo is tipo]


def test_frase_valida_produce_los_cuatro_tipos_menos_aviso(catalogo):
    sistema, robot, recibidos = montar(catalogo)
    sistema.oir("Perro, siéntate")
    assert de_tipo(recibidos, TipoEvento.ESTADO_CONEXION) == ["conectado"]  # U2: al arrancar
    assert de_tipo(recibidos, TipoEvento.TEXTO_RECONOCIDO) == ["Perro, siéntate"]
    assert de_tipo(recibidos, TipoEvento.ORDEN_INTERPRETADA) == ["REQ-02"]
    assert de_tipo(recibidos, TipoEvento.AVISO) == []
    assert robot.cadenas == ["ksit"]


def test_frase_invalida_produce_texto_y_aviso_sin_orden(catalogo):
    sistema, robot, recibidos = montar(catalogo)
    sistema.oir("Perro, 3 4 5 6 7 8 9 10")
    assert de_tipo(recibidos, TipoEvento.TEXTO_RECONOCIDO) == ["Perro, 3 4 5 6 7 8 9 10"]
    assert de_tipo(recibidos, TipoEvento.ORDEN_INTERPRETADA) == []
    assert de_tipo(recibidos, TipoEvento.AVISO) == [AVISO_NO_ENTENDIDA]
    assert robot.cadenas == []


def test_sin_robot_el_estado_es_desconectado_desde_el_arranque(catalogo):
    """REQ-25 y U2: la interfaz sabe que no hay robot antes de la primera orden."""
    sistema, robot, recibidos = montar(catalogo, conectado=False)
    assert de_tipo(recibidos, TipoEvento.ESTADO_CONEXION) == ["desconectado"]
    sistema.oir("Perro, siéntate")
    assert de_tipo(recibidos, TipoEvento.AVISO) == [AVISO_NO_CONECTADO]
    assert robot.cadenas == []


def test_perder_y_recuperar_la_conexion_publica_cada_cambio(catalogo):
    sistema, robot, recibidos = montar(catalogo)
    robot.simular_sin_conexion()
    sistema.tick()
    sistema.tick()  # sin cambio: no se repite
    robot._conectado = True
    sistema.tick()
    assert de_tipo(recibidos, TipoEvento.ESTADO_CONEXION) == ["conectado", "desconectado", "conectado"]


def test_fallo_al_enviar_publica_desconectado_una_vez(catalogo):
    sistema, robot, recibidos = montar(catalogo)
    robot.fallo_envio = True
    sistema.oir("Perro, siéntate")
    sistema.tick()
    assert de_tipo(recibidos, TipoEvento.ESTADO_CONEXION) == ["conectado", "desconectado"]
    assert AVISO_CONEXION_PERDIDA in de_tipo(recibidos, TipoEvento.AVISO)
