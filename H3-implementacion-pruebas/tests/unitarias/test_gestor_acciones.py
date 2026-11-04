"""Pruebas unitarias del gestor de acciones con robot y reloj simulados (sin robot, REQ-26).

Cubre REQ-07, REQ-25, REQ-29 a REQ-33 (D-06, D-10, D-11, D-13). Las duraciones son valores de prueba.
"""
from __future__ import annotations

import dataclasses

import pytest

from atenio.ajustes import cargar_ajustes
from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import (
    AVISO_BATERIA_BAJA,
    AVISO_CONEXION_PERDIDA,
    AVISO_NO_CONECTADO,
    AVISO_PARADA_ACTIVA,
    TipoEvento,
)
from atenio.gestor_acciones import Estado, GestorAcciones, aviso_duracion_sin_medir
from atenio.modelos import Interpretacion, Orden, Paso, TipoInterpretacion
from atenio.reloj import RelojSimulado

T = 10.0  # T reducido para las pruebas (REQ-31: «Sin robot con T reducido»)

# Órdenes de prueba con duraciones inventadas para la prueba (no son medidas del robot).
SIENTATE = Orden("REQ-02", ("siéntate",), (Paso("ksit", 2.0),))
LEVANTATE = Orden("REQ-03", ("levántate",), (Paso("kup", 1.0),))
CAMINA = Orden("REQ-04", ("camina",), (Paso("kwkF", 3.0),))
CAMINA_SIN_DURACION = Orden("REQ-04", ("camina",), (Paso("kwkF", None),))
PARA = Orden("REQ-07", ("para",), (Paso("krest", None),), interrumpe=True)
VUELTA = Orden("REQ-16", ("da una vuelta",), (Paso("kwkL", 1.5), Paso("kwkL", 1.5)))


def ordenes(*o: Orden) -> Interpretacion:
    return Interpretacion(TipoInterpretacion.ORDENES, tuple(o))


@pytest.fixture
def robot(reloj) -> EnlaceSimulado:
    return EnlaceSimulado(reloj)


@pytest.fixture
def gestor(robot, reloj) -> GestorAcciones:
    return GestorAcciones(robot, reloj, inactividad_s=T)


def avanzar(gestor: GestorAcciones, reloj: RelojSimulado, s: float) -> None:
    reloj.avanzar(s)
    gestor.tick()


# ------------------------------------------------------------------ una orden y la cola


def test_orden_con_robot_libre_se_envia_en_el_acto(gestor, robot):
    gestor.recibir(ordenes(SIENTATE))
    assert robot.registro == [(0.0, "ksit")]
    assert gestor.estado is Estado.OCUPADO


def test_la_accion_termina_al_pasar_su_duracion(gestor, robot, reloj):
    gestor.recibir(ordenes(SIENTATE))
    avanzar(gestor, reloj, 1.9)
    assert gestor.estado is Estado.OCUPADO
    avanzar(gestor, reloj, 0.1)
    assert gestor.estado is Estado.LIBRE


def test_dos_ordenes_en_una_frase_van_en_orden_y_la_segunda_al_terminar_la_primera(gestor, robot, reloj):
    """REQ-29, SC-009."""
    gestor.recibir(ordenes(CAMINA, SIENTATE))
    assert robot.cadenas == ["kwkF"]
    avanzar(gestor, reloj, 2.9)
    assert robot.cadenas == ["kwkF"]
    avanzar(gestor, reloj, 0.1)
    assert robot.registro == [(0.0, "kwkF"), (3.0, "ksit")]


def test_tres_ordenes_en_una_frase(gestor, robot, reloj):
    """REQ-29, SC-009."""
    gestor.recibir(ordenes(LEVANTATE, CAMINA, SIENTATE))
    for _ in range(10):
        avanzar(gestor, reloj, 0.5)
    assert robot.registro == [(0.0, "kup"), (1.0, "kwkF"), (4.0, "ksit")]


def test_tres_ordenes_con_robot_ocupado_se_envian_en_orden_de_llegada(robot, reloj):
    """REQ-32, SC-010, en modo cola (nueva_orden_interrumpe = false)."""
    ajustes = dataclasses.replace(cargar_ajustes(), nueva_orden_interrumpe=False)
    gestor = GestorAcciones(robot, reloj, ajustes=ajustes, inactividad_s=T)
    gestor.recibir(ordenes(CAMINA))
    avanzar(gestor, reloj, 0.5)
    gestor.recibir(ordenes(SIENTATE))
    gestor.recibir(ordenes(LEVANTATE))
    gestor.recibir(ordenes(CAMINA))
    assert robot.cadenas == ["kwkF"]
    assert [p.comando for p in gestor.cola] == ["ksit", "kup", "kwkF"]
    for _ in range(16):  # 8 s: antes de T
        avanzar(gestor, reloj, 0.5)
    assert robot.registro == [(0.0, "kwkF"), (3.0, "ksit"), (5.0, "kup"), (6.0, "kwkF")]
    avanzar(gestor, reloj, 1.0)  # t = 9: fin del último paso
    assert gestor.estado is Estado.LIBRE


def test_orden_con_varios_pasos_los_envia_uno_tras_otro(gestor, robot, reloj):
    """REQ-14 a REQ-16: la lista de comandos enviada es la del catálogo."""
    gestor.recibir(ordenes(VUELTA))
    avanzar(gestor, reloj, 1.5)
    assert robot.registro == [(0.0, "kwkL"), (1.5, "kwkL")]


def test_un_tick_tarde_envia_todos_los_pasos_vencidos(gestor, robot, reloj):
    gestor.recibir(ordenes(LEVANTATE, SIENTATE))
    avanzar(gestor, reloj, 100.0)
    assert robot.cadenas == ["kup", "ksit"]


def test_avisos_del_interprete_pasan_a_la_interfaz(gestor, robot):
    """REQ-29: la orden saltada produce un aviso; REQ-12/REQ-13: sin comando."""
    gestor.recibir(Interpretacion(TipoInterpretacion.ORDENES, (CAMINA,), ("orden no disponible: «bailoteo»",)))
    gestor.recibir(Interpretacion(TipoInterpretacion.NO_ENTENDIDA, (), ("no se ha entendido bien",)))
    assert robot.cadenas == ["kwkF"]
    assert gestor.eventos.avisos == ["orden no disponible: «bailoteo»", "no se ha entendido bien"]


@pytest.mark.parametrize("tipo", [t for t in TipoInterpretacion if t is not TipoInterpretacion.ORDENES])
def test_solo_ordenes_produce_comandos(gestor, robot, tipo):
    gestor.recibir(Interpretacion(tipo))
    assert robot.registro == []


def test_orden_interpretada_se_publica(gestor):
    gestor.recibir(ordenes(SIENTATE))
    assert gestor.eventos.textos(TipoEvento.ORDEN_INTERPRETADA) == ["REQ-02"]


# ------------------------------------------------------------------ duración sin medir (P-03)


@pytest.mark.pendiente("P-03")
def test_paso_sin_duracion_no_termina_solo_y_la_cola_espera(gestor, robot, reloj):
    gestor.recibir(ordenes(CAMINA_SIN_DURACION, SIENTATE))
    avanzar(gestor, reloj, T - 0.1)
    assert robot.cadenas == ["kwkF"]
    assert gestor.estado is Estado.OCUPADO
    assert aviso_duracion_sin_medir("kwkF") in gestor.eventos.avisos


@pytest.mark.pendiente("P-03")
def test_paso_sin_duracion_lo_corta_el_reposo_por_inactividad(gestor, robot, reloj):
    gestor.recibir(ordenes(CAMINA_SIN_DURACION, SIENTATE))
    avanzar(gestor, reloj, T)
    assert robot.cadenas == ["kwkF", "krest"]
    assert gestor.cola == ()
    assert gestor.estado is Estado.REPOSO


@pytest.mark.pendiente("P-03")
def test_duracion_desconocida_configurable(robot, reloj):
    gestor = GestorAcciones(robot, reloj, inactividad_s=T, duracion_desconocida_s=4.0)
    gestor.recibir(ordenes(CAMINA_SIN_DURACION, SIENTATE))
    avanzar(gestor, reloj, 4.0)
    assert robot.registro == [(0.0, "kwkF"), (4.0, "ksit")]


# ------------------------------------------------------------------ «para» (REQ-07, D-10)


def test_para_con_accion_en_curso_envia_krest_en_el_acto_y_no_se_encola(gestor, robot, reloj):
    """REQ-07, SC-012."""
    gestor.recibir(ordenes(CAMINA))
    avanzar(gestor, reloj, 1.0)
    gestor.recibir(ordenes(PARA))
    assert robot.registro == [(0.0, "kwkF"), (1.0, "krest")]
    assert all(p.comando != "krest" for p in gestor.cola)
    assert gestor.estado is Estado.LIBRE


@pytest.mark.discrepancia("OPEN-12")
def test_para_vacia_la_cola(gestor, robot, reloj):
    """D-10, opción A (ajuste para_vacia_cola = true)."""
    gestor.recibir(ordenes(CAMINA, SIENTATE, LEVANTATE))
    gestor.recibir(ordenes(PARA))
    avanzar(gestor, reloj, T - 1)  # antes del reposo por inactividad
    assert robot.cadenas == ["kwkF", "krest"]
    assert gestor.cola == ()


@pytest.mark.discrepancia("OPEN-12")
def test_para_sin_vaciar_la_cola_sigue_con_la_siguiente(robot, reloj):
    """D-10, opción B: solo cambia el ajuste."""
    ajustes = dataclasses.replace(cargar_ajustes(), para_vacia_cola=False)
    gestor = GestorAcciones(robot, reloj, ajustes=ajustes, inactividad_s=T)
    gestor.recibir(ordenes(CAMINA, SIENTATE))
    gestor.recibir(ordenes(PARA))
    assert robot.cadenas == ["kwkF", "krest", "ksit"]


def test_para_con_robot_libre_envia_krest(gestor, robot):
    gestor.recibir(ordenes(PARA))
    assert robot.cadenas == ["krest"]
    assert gestor.estado is Estado.LIBRE


# ------------------------------------------------------------------ parada de emergencia (REQ-30)


@pytest.mark.discrepancia("Y-03")
def test_boton_envia_el_comando_de_parada_y_vacia_la_cola(gestor, robot, reloj):
    """D-11: comando de parada `d` (ajuste provisional, OPEN-11)."""
    gestor.recibir(ordenes(CAMINA, SIENTATE))
    avanzar(gestor, reloj, 1.0)
    gestor.pulsar_parada()
    assert robot.registro == [(0.0, "kwkF"), (1.0, "d")]
    assert gestor.cola == ()
    assert gestor.estado is Estado.PARADA
    avanzar(gestor, reloj, 20.0)
    assert robot.cadenas == ["kwkF", "d"]


def test_con_parada_activa_ninguna_de_10_ordenes_produce_comando(gestor, robot):
    """REQ-30, SC-011."""
    gestor.pulsar_parada()
    for _ in range(10):
        gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["d"]
    assert gestor.eventos.avisos.count(AVISO_PARADA_ACTIVA) == 11  # 1 al pulsar + 10 órdenes


def test_para_tambien_se_ignora_con_parada_activa(gestor, robot):
    gestor.pulsar_parada()
    gestor.recibir(ordenes(PARA))
    assert robot.cadenas == ["d"]


def test_segundo_clic_desactiva_y_la_siguiente_orden_se_ejecuta(gestor, robot):
    """REQ-30, SC-011."""
    gestor.pulsar_parada()
    gestor.recibir(ordenes(SIENTATE))
    gestor.pulsar_parada()
    assert gestor.estado is Estado.LIBRE
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["d", "ksit"]


def test_parada_manda_sobre_el_reposo_por_inactividad(gestor, robot, reloj):
    """Casos límite de spec.md: con la parada activa, REQ-30 manda sobre REQ-31."""
    gestor.pulsar_parada()
    avanzar(gestor, reloj, 3 * T)
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["d"]
    assert gestor.estado is Estado.PARADA


def test_boton_desde_reposo(gestor, robot, reloj):
    avanzar(gestor, reloj, T)
    gestor.pulsar_parada()
    assert robot.cadenas == ["krest", "d"]
    assert gestor.estado is Estado.PARADA


# ------------------------------------------------------------------ reposo por inactividad (REQ-31)


def test_reposo_tras_T_sin_ordenes_sin_aviso(gestor, robot, reloj):
    """REQ-31, ESC-03: el simulador recibe el comando de reposo (OPEN-11) y no hay aviso."""
    avanzar(gestor, reloj, T - 0.1)
    assert robot.registro == []
    avanzar(gestor, reloj, 0.1)
    assert robot.registro == [(T, "krest")]
    assert gestor.estado is Estado.REPOSO
    assert gestor.eventos.avisos == []


def test_reposo_se_envia_una_sola_vez(gestor, robot, reloj):
    for _ in range(5):
        avanzar(gestor, reloj, T)
    assert robot.cadenas == ["krest"]


def test_T_cuenta_desde_la_ultima_orden(gestor, robot, reloj):
    avanzar(gestor, reloj, T / 2)
    gestor.recibir(ordenes(SIENTATE))
    avanzar(gestor, reloj, T - 0.1)
    assert robot.cadenas == ["ksit"]
    avanzar(gestor, reloj, 0.1)
    assert robot.cadenas == ["ksit", "krest"]


def test_orden_valida_saca_del_reposo_y_se_ejecuta(gestor, robot, reloj):
    """REQ-31, escenario 2 de la historia 7."""
    avanzar(gestor, reloj, T)
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["krest", "ksit"]
    assert gestor.estado is Estado.OCUPADO


def test_T_por_defecto_es_el_de_la_demostracion(robot, reloj):
    assert GestorAcciones(robot, reloj)._inactividad_s == cargar_ajustes().inactividad_demo_s == 300


# ------------------------------------------------------------------ conexión (REQ-25, D-13)


def test_sin_conexion_no_envia_y_avisa(robot, reloj):
    """REQ-25, ESC-07."""
    robot.simular_sin_conexion()
    gestor = GestorAcciones(robot, reloj, inactividad_s=T)
    gestor.recibir(ordenes(SIENTATE))
    assert robot.registro == []
    assert gestor.eventos.avisos == [AVISO_NO_CONECTADO]
    assert gestor.cola == ()


def test_sin_conexion_no_hay_reposo_ni_aviso(robot, reloj):
    robot.simular_sin_conexion()
    gestor = GestorAcciones(robot, reloj, inactividad_s=T)
    avanzar(gestor, reloj, 2 * T)
    assert robot.registro == [] and gestor.eventos.avisos == []


def test_boton_sin_conexion_activa_la_parada_y_avisa(robot, reloj):
    robot.simular_sin_conexion()
    gestor = GestorAcciones(robot, reloj, inactividad_s=T)
    gestor.pulsar_parada()
    assert gestor.estado is Estado.PARADA
    assert AVISO_NO_CONECTADO in gestor.eventos.avisos


@pytest.mark.pendiente("P-08")
def test_fallo_de_envio_durante_una_accion_desconecta_vacia_la_cola_y_avisa(gestor, robot, reloj):
    """D-13: propuesta inicial para la pérdida de conexión durante una acción."""
    gestor.recibir(ordenes(CAMINA, SIENTATE, LEVANTATE))
    robot.fallo_envio = True
    avanzar(gestor, reloj, 3.0)
    assert robot.cadenas == ["kwkF"]
    assert not robot.conectado
    assert gestor.cola == ()
    assert gestor.estado is Estado.LIBRE
    assert gestor.eventos.avisos == [AVISO_CONEXION_PERDIDA]
    assert gestor.eventos.textos(TipoEvento.ESTADO_CONEXION) == ["desconectado"]


@pytest.mark.pendiente("P-08")
def test_tras_perder_la_conexion_las_ordenes_avisan_robot_no_conectado(gestor, robot, reloj):
    gestor.recibir(ordenes(CAMINA))
    robot.fallo_envio = True
    gestor.recibir(ordenes(PARA))
    gestor.recibir(ordenes(SIENTATE))
    assert robot.cadenas == ["kwkF"]
    assert gestor.eventos.avisos[-1] == AVISO_NO_CONECTADO


# ------------------------------------------------------------------ batería baja (REQ-33)


def test_low_power_produce_aviso_de_bateria_baja(gestor, robot):
    """REQ-33, ESC-08: el simulador envía «Low power: 6.5V»."""
    robot.inyectar_linea("Low power: 6.5V")
    gestor.tick()
    assert gestor.eventos.avisos == [AVISO_BATERIA_BAJA]
    assert robot.registro == []


def test_otras_lineas_del_robot_no_avisan(gestor, robot):
    robot.inyectar_linea("k")
    gestor.tick()
    assert gestor.eventos.avisos == []


# ------------------------------------------------------------------ T060, U2: estado de conexión como evento


def test_conectar_publica_el_estado_al_arrancar():
    reloj = RelojSimulado()
    robot = EnlaceSimulado(reloj, conectado=False)
    gestor = GestorAcciones(robot, reloj)
    assert gestor.conectar() is True  # el simulado se conecta al pedirlo
    assert gestor.eventos.textos(TipoEvento.ESTADO_CONEXION) == ["conectado"]


def test_tick_publica_solo_los_cambios_de_conexion():
    reloj = RelojSimulado()
    robot = EnlaceSimulado(reloj)
    gestor = GestorAcciones(robot, reloj)
    gestor.tick()  # antes de conectar() no se publica nada
    assert gestor.eventos.textos(TipoEvento.ESTADO_CONEXION) == []
    gestor.conectar()
    robot.simular_sin_conexion()
    gestor.tick()
    gestor.tick()
    assert gestor.eventos.textos(TipoEvento.ESTADO_CONEXION) == ["conectado", "desconectado"]
