"""Herramienta de medición de la sesión 2 (T069, T070, T071, T080), sin robot (REQ-26).

Se prueba con robot y reloj simulados; las duraciones son de prueba, no medidas del Bittle.
"""
from __future__ import annotations

import csv

import pytest
import serial

from atenio.enlace.medicion import ErrorMedicion, SesionMedida, interpretar_fin_de_linea
from atenio.enlace.serie import EnlaceSerie
from atenio.enlace.simulado import EnlaceSimulado


@pytest.fixture
def robot(reloj):
    return EnlaceSimulado(reloj)


@pytest.fixture
def sesion(robot, reloj):
    return SesionMedida(robot, reloj)


def test_cronometra_desde_el_envio_hasta_el_fin(sesion, robot, reloj):
    sesion.enviar("ksit")
    reloj.avanzar(1.234)
    medida = sesion.terminar()
    assert robot.cadenas == ["ksit"]
    assert medida.duracion_s == 1.23
    assert sesion.medidas == [medida]
    assert sesion.en_curso is None


def test_guarda_lo_que_devuelve_el_robot(sesion, robot, reloj):
    sesion.enviar("kup")
    robot.inyectar_linea("k")
    reloj.avanzar(0.5)
    robot.inyectar_linea("Low power: 6.5V")
    assert sesion.terminar().respuestas == ["k", "Low power: 6.5V"]


def test_marcha_continua_se_guarda_sin_duracion(sesion, reloj):
    sesion.enviar("kwkF")
    reloj.avanzar(10)
    medida = sesion.terminar(None, nota="no termina solo")
    assert medida.duracion_s is None and medida.nota == "no termina solo"


def test_enviar_otro_cierra_el_anterior_sin_duracion(sesion, robot, reloj):
    sesion.enviar("kwkF")
    reloj.avanzar(3)
    sesion.enviar("d")
    assert robot.cadenas == ["kwkF", "d"]
    assert sesion.medidas[0].duracion_s is None
    assert "interrumpido" in sesion.medidas[0].nota
    assert sesion.en_curso.comando == "d"


@pytest.mark.parametrize("comando", ["G", "g", " g "])
def test_nunca_envia_el_giroscopio(sesion, robot, comando):
    with pytest.raises(ErrorMedicion):
        sesion.enviar(comando)
    assert robot.registro == []


def test_sin_conexion_no_envia(sesion, robot):
    robot.simular_sin_conexion()
    with pytest.raises(ErrorMedicion, match="no conectado"):
        sesion.enviar("ksit")


def test_fallo_de_envio_avisa(sesion, robot):
    robot.fallo_envio = True
    with pytest.raises(ErrorMedicion, match="conexión"):
        sesion.enviar("ksit")
    assert sesion.en_curso is None


def test_terminar_sin_comando_en_curso_es_error(sesion):
    with pytest.raises(ErrorMedicion):
        sesion.terminar()


def test_guarda_el_csv(sesion, robot, reloj, tmp_path):
    sesion.enviar("ksit")
    robot.inyectar_linea("k")
    reloj.avanzar(2)
    sesion.terminar()
    sesion.enviar("kwkF")
    sesion.terminar(None, nota="no termina solo")
    ruta = sesion.guardar_csv(tmp_path / "ensayos" / "sesion.csv")
    with open(ruta, encoding="utf-8") as f:
        filas = list(csv.reader(f))
    assert filas == [
        ["comando", "duracion_s", "respuestas", "nota"],
        ["ksit", "2.00", "k", ""],
        ["kwkF", "", "", "no termina solo"],
    ]


@pytest.mark.parametrize("texto, esperado", [("\\n", "\n"), ("\\r\\n", "\r\n"), ("ninguno", "")])
def test_fin_de_linea_escrito_en_la_consola(texto, esperado):
    assert interpretar_fin_de_linea(texto) == esperado


# ------------------------------------------------------------------ enlace serie (T060, T061)


def test_enlace_serie_se_marca_desconectado_si_falla_la_lectura():
    """Cable quitado durante la sesión: leer falla, el enlace pasa a desconectado y el gestor lo publica."""
    e = EnlaceSerie("loop://")
    e.conectar()

    def mal(_n):
        raise serial.SerialException("cable")

    e._ser.read = mal
    assert e.leer_lineas() == []
    assert not e.conectado
