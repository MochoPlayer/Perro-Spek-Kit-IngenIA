"""Cada orden nueva interrumpe la anterior (ajuste nueva_orden_interrumpe, petición del equipo del 04/11).

Sin robot: robot y reloj simulados (REQ-26). Las duraciones son valores de prueba.
"""
from __future__ import annotations

import dataclasses

import pytest

from atenio.ajustes import cargar_ajustes
from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import AVISO_PARADA_ACTIVA
from atenio.gestor_acciones import Estado, GestorAcciones
from atenio.modelos import Interpretacion, Orden, Paso, TipoInterpretacion

SIENTATE = Orden("REQ-02", ("siéntate",), (Paso("ksit", 2.0),))
LEVANTATE = Orden("REQ-03", ("levántate",), (Paso("kup", 1.0),))
CAMINA = Orden("REQ-04", ("camina",), (Paso("kwkF", None),))  # marcha: no termina sola
PARA = Orden("REQ-07", ("para",), (Paso("krest", None),), interrumpe=True)
VUELTA = Orden("REQ-16", ("da una vuelta",), (Paso("kwkL", 1.5), Paso("kwkL", 1.5)))
T = 30.0


def ordenes(*o: Orden) -> Interpretacion:
    return Interpretacion(TipoInterpretacion.ORDENES, tuple(o))


@pytest.fixture
def robot(reloj):
    return EnlaceSimulado(reloj)


@pytest.fixture
def gestor(robot, reloj):
    ajustes = dataclasses.replace(cargar_ajustes(), nueva_orden_interrumpe=True)
    return GestorAcciones(robot, reloj, ajustes=ajustes, inactividad_s=T)


def avanzar(gestor, reloj, s):
    reloj.avanzar(s)
    gestor.tick()


def test_el_ajuste_viene_activado_en_ajustes_json():
    assert cargar_ajustes().nueva_orden_interrumpe is True


def test_orden_nueva_corta_la_marcha_y_se_envia_en_el_acto(gestor, robot, reloj):
    gestor.recibir(ordenes(CAMINA))
    avanzar(gestor, reloj, 3.0)
    gestor.recibir(ordenes(SIENTATE))
    assert robot.registro == [(0.0, "kwkF"), (3.0, "ksit")]
    assert gestor.estado is Estado.OCUPADO


def test_orden_nueva_corta_una_postura_a_medias(gestor, robot, reloj):
    gestor.recibir(ordenes(SIENTATE))
    avanzar(gestor, reloj, 0.5)
    gestor.recibir(ordenes(LEVANTATE))
    assert robot.cadenas == ["ksit", "kup"]
    avanzar(gestor, reloj, 1.0)  # kup dura 1 s: termina; ksit ya no cuenta
    assert gestor.estado is Estado.LIBRE


def test_orden_nueva_descarta_los_pasos_que_quedaban(gestor, robot, reloj):
    gestor.recibir(ordenes(VUELTA))
    gestor.recibir(ordenes(SIENTATE))
    avanzar(gestor, reloj, 10.0)
    assert robot.cadenas == ["kwkL", "ksit"]
    assert gestor.cola == ()


def test_las_ordenes_de_la_misma_frase_siguen_en_orden(gestor, robot, reloj):
    gestor.recibir(ordenes(CAMINA))
    gestor.recibir(ordenes(SIENTATE, LEVANTATE))
    assert robot.cadenas == ["kwkF", "ksit"]
    avanzar(gestor, reloj, 2.0)
    assert robot.cadenas == ["kwkF", "ksit", "kup"]


def test_ejecutadas_lleva_la_cuenta_de_lo_enviado(gestor):
    gestor.recibir(ordenes(CAMINA))
    gestor.recibir(ordenes(SIENTATE))
    assert gestor.ejecutadas == ["REQ-04", "REQ-02"]
    assert gestor.cola_ordenes == ()


def test_para_sigue_igual(gestor, robot, reloj):
    gestor.recibir(ordenes(CAMINA))
    avanzar(gestor, reloj, 1.0)
    gestor.recibir(ordenes(PARA))
    assert robot.cadenas == ["kwkF", "krest"]
    assert gestor.estado is Estado.LIBRE


def test_con_parada_activa_no_interrumpe_ni_envia(gestor, robot):
    gestor.pulsar_parada()
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["d"]
    assert gestor.estado is Estado.PARADA
    assert gestor.eventos.avisos[-1] == AVISO_PARADA_ACTIVA


def test_desde_el_reposo_la_orden_se_ejecuta(gestor, robot, reloj):
    avanzar(gestor, reloj, T)
    assert gestor.estado is Estado.REPOSO
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["krest", "ksit"]


def test_sin_conexion_no_corta_nada(gestor, robot):
    gestor.recibir(ordenes(CAMINA))
    robot.simular_sin_conexion()
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["kwkF"]
