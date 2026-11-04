"""Pruebas de principal.py (T019, T045, T057 en parte): montaje, elección del enlace y voz con una escucha falsa.

Cubre REQ-26 y REQ-27. Sin robot, sin micrófono y sin red.
"""
from __future__ import annotations

import json
import time

import pytest

from atenio.ajustes import cargar_ajustes
from atenio.enlace.serie import EnlaceSerie
from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import TipoEvento
from atenio.gestor_acciones import Estado
from atenio.principal import Sistema, crear_enlace, crear_sistema, tipo_enlace_de_ajustes
from atenio.reloj import RelojReal, RelojSimulado


class EscuchaDePrueba:
    """Sigue el contrato de atenio.escucha.Escucha. `decir()` hace lo que haría el hilo de la voz."""

    def __init__(self) -> None:
        self.activa = False
        self._al_oir = None

    def iniciar(self, al_oir) -> None:
        self._al_oir = al_oir
        self.activa = True

    def parar(self) -> None:
        self.activa = False

    def decir(self, texto: str) -> None:
        self._al_oir(texto)


def test_la_voz_llega_igual_que_una_frase_escrita(catalogo):
    reloj = RelojSimulado()
    robot = EnlaceSimulado(reloj)
    escucha = EscuchaDePrueba()
    sistema = Sistema(robot, reloj, catalogo=catalogo, escucha=escucha)
    assert not sistema.voz_activa
    sistema.arrancar(con_bucle=False)
    assert sistema.voz_activa
    escucha.decir("Perro, siéntate")
    sistema.oir("Perro, saluda")  # caja de texto
    assert sistema.eventos.textos(TipoEvento.TEXTO_RECONOCIDO) == ["Perro, siéntate", "Perro, saluda"]
    assert robot.cadenas[0] == "ksit"
    sistema.detener()
    assert not escucha.activa


def test_texto_vacio_no_publica_nada(catalogo):
    reloj = RelojSimulado()
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo)
    sistema.oir("   ")
    assert sistema.eventos.lista == []


def test_el_registro_de_la_interfaz_anota_lo_enviado(catalogo):
    reloj = RelojSimulado(10)  # el registro cuenta desde el arranque
    robot = EnlaceSimulado(reloj)
    sistema = Sistema(robot, reloj, catalogo=catalogo)
    sistema.arrancar(con_bucle=False)
    sistema.oir("Perro, siéntate")
    foto = sistema.foto()
    assert foto["registro"] == [{"t": 0.0, "comando": "ksit"}]
    assert foto["conectado"] is True
    assert foto["estado"] == Estado.OCUPADO.value


def test_parada_desde_el_sistema(catalogo):
    reloj = RelojSimulado()
    robot = EnlaceSimulado(reloj)
    sistema = Sistema(robot, reloj, catalogo=catalogo)
    sistema.arrancar(con_bucle=False)
    sistema.pulsar_parada()
    assert sistema.foto()["parada"] is True
    assert robot.cadenas == [cargar_ajustes().comando_parada]
    sistema.pulsar_parada()
    assert sistema.foto()["parada"] is False


def test_el_bucle_llama_a_tick_con_el_reloj_real(catalogo):
    """El gestor avanza solo: `ksit` dura 2 s en el catálogo; con 0,2 s basta para ver que el hilo corre."""
    reloj = RelojReal()
    robot = EnlaceSimulado(reloj)
    sistema = Sistema(robot, reloj, catalogo=catalogo)
    llamadas = []
    original = sistema.gestor.tick
    sistema.gestor.tick = lambda: (llamadas.append(1), original())  # type: ignore[method-assign]
    sistema.arrancar()
    try:
        time.sleep(0.2)
    finally:
        sistema.detener()
    assert len(llamadas) >= 2


# ------------------------------------------------------------------ T045: enlace según ajustes.json


def test_ajustes_dice_simulado_por_defecto():
    assert tipo_enlace_de_ajustes() == "simulado"


def test_tipo_de_enlace_desde_un_fichero(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({"enlace": {"valor": "serie"}}), encoding="utf-8")
    assert tipo_enlace_de_ajustes(f) == "serie"
    f.write_text(json.dumps({}), encoding="utf-8")
    assert tipo_enlace_de_ajustes(f) == "simulado"
    f.write_text(json.dumps({"enlace": {"valor": "wifi"}}), encoding="utf-8")
    with pytest.raises(ValueError):
        tipo_enlace_de_ajustes(f)


def test_crear_enlace_simulado_y_serie():
    ajustes = cargar_ajustes()
    reloj = RelojSimulado()
    assert isinstance(crear_enlace("simulado", ajustes, reloj), EnlaceSimulado)
    serie = crear_enlace("serie", ajustes, reloj)
    assert isinstance(serie, EnlaceSerie)
    assert serie.conectado is False  # no se abre nada al crearlo


def test_serie_sin_puerto_arranca_desconectado():
    """ajustes.json tiene `puerto: null` (OPEN-07): el programa arranca y avisa, no se cae."""
    sistema = crear_sistema("serie", reloj=RelojSimulado())
    sistema.arrancar(con_bucle=False)
    assert sistema.eventos.textos(TipoEvento.ESTADO_CONEXION) == ["desconectado"]
    sistema.oir("Perro, siéntate")
    assert "robot no conectado" in sistema.eventos.avisos


# ---------------------------------------------------------------- botón del micro (poner_micro)


def test_sin_voz_arranca_apagado_y_el_boton_crea_la_escucha(catalogo):
    reloj = RelojSimulado()
    creadas: list[EscuchaDePrueba] = []
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo,
                      fabrica_escucha=lambda: creadas.append(EscuchaDePrueba()) or creadas[-1])
    sistema.arrancar(con_bucle=False)
    assert not sistema.voz_activa and creadas == []  # sin --voz: micro apagado
    assert sistema.poner_micro(True) is True
    assert len(creadas) == 1 and sistema.voz_activa
    creadas[0].decir("Perro, siéntate")
    assert sistema.eventos.textos(TipoEvento.TEXTO_RECONOCIDO) == ["Perro, siéntate"]
    assert sistema.poner_micro(False) is False and not creadas[0].activa
    assert sistema.poner_micro(True) is True
    assert len(creadas) == 1  # se reutiliza la misma escucha


def test_con_voz_arranca_encendido_y_se_apaga_con_el_boton(catalogo):
    reloj = RelojSimulado()
    escucha = EscuchaDePrueba()
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo, escucha=escucha)
    sistema.arrancar(con_bucle=False)
    assert sistema.voz_activa
    assert sistema.poner_micro(False) is False
    assert not escucha.activa


def test_encender_sin_voz_posible_da_un_aviso(catalogo):
    reloj = RelojSimulado()
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo)
    assert sistema.poner_micro(True) is False
    assert sistema.eventos.avisos == ["no hay voz en este programa: usa la caja de texto"]


def test_si_falla_el_motor_de_voz_sale_un_aviso_y_sigue_apagado(catalogo):
    reloj = RelojSimulado()

    def falla():
        raise RuntimeError("Falta la biblioteca «vosk»")

    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo, fabrica_escucha=falla)
    assert sistema.poner_micro(True) is False
    assert sistema.eventos.avisos == ["no se pudo encender el micro: Falta la biblioteca «vosk»"]
    assert not sistema.voz_activa


def test_nivel_sin_micro_esta_inactivo(catalogo):
    reloj = RelojSimulado()
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo)
    assert sistema.nivel(7) == {"activo": False, "umbral": None, "valores": [], "total": 7}


def test_la_foto_trae_la_orden_con_su_palabra_y_su_comando(catalogo):
    reloj = RelojSimulado()
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo)
    sistema.arrancar(con_bucle=False)
    sistema.oir("Perro, sentado")
    foto = sistema.foto()
    orden = [e for e in foto["eventos"] if e["tipo"] == "orden_interpretada"][0]
    assert orden["orden"] == {"palabra": "siéntate", "comandos": ["ksit"]}
    assert foto["enlace"] == "simulado"
    assert foto["error_voz"] is None
