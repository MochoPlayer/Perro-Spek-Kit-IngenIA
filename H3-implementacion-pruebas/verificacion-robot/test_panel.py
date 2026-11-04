"""Lógica del panel de botones (panel_robot.py), sin robot ni servidor web."""
from __future__ import annotations

import pytest

from atenio.enlace.simulado import EnlaceSimulado
from panel_robot import Panel, botones


@pytest.fixture
def robot(reloj):
    return EnlaceSimulado(reloj)


@pytest.fixture
def panel(robot):
    return Panel(robot, parada="d", reposo="krest", descripcion="simulado")


def test_la_letra_del_robot_es_un_recibido_y_no_cierra_la_medida(panel, robot):
    """Sesión del 04/11: con kwkF el robot devuelve «k» mientras sigue andando."""
    panel.enviar("kwkF")
    robot.inyectar_linea("k")
    panel.leer()
    assert panel.medidas == []
    assert panel.estado(0)["en_curso"]["respuesta_s"] is not None


def test_ha_terminado_da_la_duracion(panel, robot):
    panel.enviar("ksit")
    robot.inyectar_linea("k")
    panel.leer()
    m = panel.marcar_fin()
    assert m["duracion_s"] is not None and m["en_marcha_s"] is None
    assert m["respuestas"] == ["k"]


def test_la_parada_corta_sin_duracion_y_envia_el_comando(panel, robot):
    panel.enviar("kwkF")
    panel.pulsar_parada()
    assert robot.cadenas == ["kwkF", "d"]
    m = panel.medidas[-1]
    assert m["duracion_s"] is None and m["en_marcha_s"] is not None
    assert m["nota"] == "cortado con la parada"


def test_otro_comando_interrumpe_el_anterior(panel, robot):
    panel.enviar("kwkF")
    panel.enviar("ksit")
    assert panel.medidas[0]["nota"] == "interrumpido por otro comando"
    assert panel.estado(0)["en_curso"]["comando"] == "ksit"


@pytest.mark.parametrize("comando", ["G", "g"])
def test_bloquea_el_giroscopio(panel, robot, comando):
    ok, _ = panel.enviar(comando)
    assert not ok and robot.registro == []


def test_sin_conexion_no_envia(panel, robot):
    robot.simular_sin_conexion()
    ok, texto = panel.enviar("ksit")
    assert not ok and texto == "robot no conectado"


def test_los_botones_salen_del_catalogo():
    lista = botones()
    comandos = {b["comando"]: b["grupo"] for b in lista}
    assert len(lista) == 10  # Nivel 1 de catalogo.json
    assert comandos["ksit"] == "postura" and comandos["kwkF"] == "movimiento"
