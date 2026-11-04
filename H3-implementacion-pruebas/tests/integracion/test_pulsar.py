"""Pruebas de «mantener pulsado para hablar», la cola y las ejecutadas (petición de Mario, 04/11).

Sin micrófono, sin robot y sin red: captura falsa, transcriptor falso y robot simulado.
"""
from __future__ import annotations

import threading
import time

from atenio.audio import MUESTRAS_POR_BLOQUE
from atenio.enlace.simulado import EnlaceSimulado
from atenio.escucha import EscuchaMicrofono
from atenio.principal import Sistema
from atenio.reloj import RelojSimulado
from atenio.transcripcion import TranscriptorFalso

BLOQUE = b"\x00\x00" * MUESTRAS_POR_BLOQUE


class CapturaFalsa:
    """Entrega bloques cuando el guion lo manda; `guion(escucha)` decide cuándo se pulsa y se suelta."""

    def __init__(self, guion) -> None:
        self.medidor = None
        self._guion = guion
        self.escucha = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def vaciar(self) -> None:
        pass

    def bloques(self, parar):
        yield from self._guion(self.escucha)
        parar.wait(2)


def esperar(condicion, limite_s: float = 2.0) -> None:
    fin = time.monotonic() + limite_s
    while not condicion():
        assert time.monotonic() < fin, "tiempo agotado"
        time.sleep(0.01)


def test_pulsar_graba_solo_lo_pulsado_mas_una_cola_corta():
    def guion(escucha):
        for _ in range(5):
            yield BLOQUE, 0.0
        escucha.pulsar(True)
        for _ in range(10):
            yield BLOQUE, 0.0
        escucha.pulsar(False)
        for _ in range(10):  # solo 4 de estos entran (0,2 s de cola)
            yield BLOQUE, 0.0

    captura = CapturaFalsa(guion)
    transcriptor = TranscriptorFalso(["siéntate"])
    escucha = EscuchaMicrofono(transcriptor, captura=captura, modo="pulsar", prerrollo_s=0.1)
    captura.escucha = escucha
    oidas: list[str] = []
    escucha.iniciar(oidas.append)
    esperar(lambda: oidas)
    escucha.parar()
    assert oidas == ["siéntate"]
    assert transcriptor.recibido == [(2 + 10 + 4) * 2 * MUESTRAS_POR_BLOQUE]  # 2 de prerrollo + 10 pulsados + 4 de cola


def test_un_toque_muy_corto_no_se_transcribe():
    def guion(escucha):
        escucha.pulsar(True)
        yield BLOQUE, 0.0
        escucha.pulsar(False)
        for _ in range(8):
            yield BLOQUE, 0.0

    captura = CapturaFalsa(guion)
    transcriptor = TranscriptorFalso(["no debe salir"])
    escucha = EscuchaMicrofono(transcriptor, captura=captura, modo="pulsar", prerrollo_s=0)
    captura.escucha = escucha
    oidas: list[str] = []
    escucha.iniciar(oidas.append)
    time.sleep(0.3)
    escucha.parar()
    assert oidas == [] and transcriptor.recibido == []


def test_en_modo_continuo_pulsar_no_hace_nada():
    escucha = EscuchaMicrofono(TranscriptorFalso(), captura=CapturaFalsa(lambda e: iter(())), modo="continuo")
    escucha.pulsar(True)
    assert escucha.hablando is False


def test_modo_desconocido_da_error():
    import pytest

    from atenio.escucha import ErrorDeVoz

    with pytest.raises(ErrorDeVoz):
        EscuchaMicrofono(TranscriptorFalso(), captura=CapturaFalsa(lambda e: iter(())), modo="raro")


class EscuchaPulsarDePrueba:
    """Contrato de la escucha en modo pulsar, sin hilo."""

    modo = "pulsar"

    def __init__(self) -> None:
        self.activa = False
        self.hablando = False
        self._al_oir = None

    def iniciar(self, al_oir) -> None:
        self._al_oir, self.activa = al_oir, True

    def parar(self) -> None:
        self.activa = False

    def pulsar(self, activo: bool) -> None:
        self.hablando = activo

    def decir(self, texto: str) -> None:
        self._al_oir(texto)


def _sistema(catalogo, escucha=None):
    reloj = RelojSimulado()
    sistema = Sistema(EnlaceSimulado(reloj), reloj, catalogo=catalogo, escucha=escucha)
    sistema.arrancar(con_bucle=False)
    return reloj, sistema


def test_con_pulsar_no_hace_falta_decir_perro(catalogo):
    escucha = EscuchaPulsarDePrueba()
    _, sistema = _sistema(catalogo, escucha)
    escucha.decir("siéntate")
    assert [e["tipo"] for e in sistema.foto(0)["eventos"] if e["tipo"] == "orden_interpretada"] == ["orden_interpretada"]
    assert sistema.foto(0)["ejecutadas"] == [{"palabra": "siéntate", "comandos": ["ksit"]}]


def test_con_pulsar_perro_al_principio_no_se_duplica(catalogo):
    escucha = EscuchaPulsarDePrueba()
    _, sistema = _sistema(catalogo, escucha)
    escucha.decir("Perro, siéntate")
    ordenes = [e for e in sistema.foto(0)["eventos"] if e["tipo"] == "orden_interpretada"]
    assert len(ordenes) == 1


def test_hablar_llega_a_la_escucha_y_nivel_dice_el_modo(catalogo):
    escucha = EscuchaPulsarDePrueba()
    _, sistema = _sistema(catalogo, escucha)
    assert sistema.hablar(True) is True and escucha.hablando
    assert sistema.hablar(False) is False and not escucha.hablando


def test_hablar_sin_escucha_no_falla(catalogo):
    _, sistema = _sistema(catalogo)
    assert sistema.hablar(True) is False


def test_la_pantalla_no_recibe_avisos_de_ordenes_no_reconocidas(catalogo):
    _, sistema = _sistema(catalogo)
    sistema.oir("Perro, bla bla 123")  # no entendida
    sistema.oir("Perro, bailar tango")  # fuera del catálogo
    avisos = [e for e in sistema.foto(0)["eventos"] if e["tipo"] == "aviso"]
    assert avisos and all(e["oculto"] for e in avisos)


def test_cola_y_ejecutadas_siguen_a_cada_orden(catalogo):
    reloj, sistema = _sistema(catalogo)
    sistema.oir("Perro, siéntate y luego levántate")
    foto = sistema.foto(0)
    assert foto["cola_ordenes"] == ["levántate"]
    assert foto["ejecutadas"] == [{"palabra": "siéntate", "comandos": ["ksit"]}]
    reloj.avanzar(60)
    sistema.tick()
    foto = sistema.foto(0)
    assert foto["cola_ordenes"] == []
    assert [o["palabra"] for o in foto["ejecutadas"]] == ["levántate", "siéntate"]  # la más nueva primero


def test_para_se_cuenta_como_ejecutada_y_vacia_la_cola(catalogo):
    _, sistema = _sistema(catalogo)
    sistema.oir("Perro, siéntate y luego levántate")
    sistema.oir("Perro, para")
    foto = sistema.foto(0)
    assert foto["cola_ordenes"] == []
    assert foto["ejecutadas"][0] == {"palabra": "para", "comandos": ["krest"]}
