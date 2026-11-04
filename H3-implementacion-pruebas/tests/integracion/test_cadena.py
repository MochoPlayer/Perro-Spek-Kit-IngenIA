"""Integración sin robot: texto → intérprete → gestor → robot simulado (plan.md, pasos 2 y 3).

Historias 1 a 5 y 7 de spec.md. Cubre SC-002, SC-005, SC-006, SC-009 a SC-012; REQ-01, 02-13, 20, 23, 25, 26, 29-33, 35.
"""
from __future__ import annotations

import dataclasses

import pytest

from atenio.ajustes import cargar_ajustes
from atenio.catalogo import Catalogo
from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import (
    AVISO_BATERIA_BAJA,
    AVISO_NO_CONECTADO,
    AVISO_PARADA_ACTIVA,
    Eventos,
    TipoEvento,
)
from atenio.gestor_acciones import Estado, GestorAcciones
from atenio.interprete import AVISO_NO_ENTENDIDA, AVISO_NO_DISPONIBLE, Interprete
from atenio.modelos import Paso
from atenio.reloj import RelojSimulado
from conftest import leer_frases

# Valor de prueba, NO medido: sustituye las duraciones `null` del catálogo (P-03) para poder
# probar la cola. Las duraciones reales se miden en la sesión 2 (I-4).
DURACION_PRUEBA_S = 1.0
T_PRUEBA_S = 30.0  # T reducido (REQ-31: «Sin robot con T reducido»)

# Comandos de la tabla del Nivel 1 de spec.md (REQ-02 a REQ-11). Se comparan con lo que registra el simulado (REQ-20).
COMANDO_NIVEL_1 = {
    "siéntate": "ksit",
    "levántate": "kup",
    "camina": "kwkF",
    "izquierda": "kwkL",
    "derecha": "kwkR",
    "para": "krest",
    "túmbate": "d",
    "saluda": "khi",
    "equilíbrate": "kbalance",
    "trota": "ktrF",
}


def con_duraciones_de_prueba(catalogo: Catalogo) -> Catalogo:
    ordenes = []
    for orden in catalogo.ordenes:
        pasos = tuple(
            Paso(p.comando, p.duracion_s if p.duracion_s is not None else DURACION_PRUEBA_S) for p in orden.pasos
        )
        ordenes.append(dataclasses.replace(orden, pasos=pasos))
    return Catalogo(ordenes)


class Cadena:
    """Monta los componentes 3, 4 y 5 como lo hará principal.py, con robot y reloj simulados."""

    def __init__(self, catalogo: Catalogo, *, conectado: bool = True, interrumpe: bool | None = None) -> None:
        self.catalogo = catalogo
        self.ajustes = cargar_ajustes()
        if interrumpe is not None:  # None: lo que diga ajustes.json
            self.ajustes = dataclasses.replace(self.ajustes, nueva_orden_interrumpe=interrumpe)
        self.reloj = RelojSimulado()
        self.robot = EnlaceSimulado(self.reloj, conectado=conectado)
        self.eventos = Eventos()
        self.interprete = Interprete(catalogo, reloj=self.reloj, espera_s=self.ajustes.espera_orden_s)
        self.gestor = GestorAcciones(
            self.robot, self.reloj, self.eventos, self.ajustes, inactividad_s=T_PRUEBA_S
        )

    def decir(self, texto: str) -> None:
        self.eventos.publicar(TipoEvento.TEXTO_RECONOCIDO, texto)
        self.gestor.recibir(self.interprete.interpretar(texto))

    def esperar(self, s: float, paso: float = 0.25) -> None:
        for _ in range(round(s / paso)):
            self.reloj.avanzar(paso)
            self.gestor.tick()

    @property
    def comandos(self) -> list[str]:
        return self.robot.cadenas

    @property
    def avisos(self) -> list[str]:
        return self.eventos.avisos


@pytest.fixture
def cadena(catalogo) -> Cadena:
    return Cadena(con_duraciones_de_prueba(catalogo))


def comando_de(catalogo: Catalogo, id_orden: str) -> list[str]:
    return [p.comando for p in catalogo.por_id(id_orden).pasos]


# ------------------------------------------------------------------ Historia 1


@pytest.mark.parametrize("orden,comando", COMANDO_NIVEL_1.items())
def test_h1_cada_orden_del_nivel_1_llega_como_su_comando(cadena, orden, comando):
    """SC-002, REQ-02 a REQ-11, REQ-20: cadena exacta registrada por el simulado."""
    cadena.decir(f"Perro, {orden}")
    assert cadena.comandos == [comando]
    assert cadena.robot.registro[0][0] == 0.0  # se envía en el acto (parte de software de REQ-21)


@pytest.mark.parametrize("frase", leer_frases("con_nombre.txt"))
def test_h1_las_20_frases_con_nombre_producen_un_comando(cadena, frase):
    """REQ-01."""
    texto, _, id_orden = (p.strip() for p in frase.partition("=>"))
    cadena.decir(texto)
    assert cadena.comandos == comando_de(cadena.catalogo, id_orden)


def test_h1_las_20_frases_sin_nombre_no_producen_comando(cadena):
    """REQ-01, SC-005, ESC-02: el sistema sigue escuchando."""
    for frase in leer_frases("sin_nombre.txt"):
        cadena.decir(frase)
        cadena.esperar(0.5)
    assert cadena.comandos == []
    assert cadena.avisos == []
    cadena.decir("Perro, siéntate")
    assert cadena.comandos == ["ksit"]


def test_h1_perro_solo_y_orden_dentro_de_la_espera(cadena):
    """REQ-35, escenario 5."""
    cadena.decir("Perro")
    cadena.esperar(cadena.ajustes.espera_orden_s - 1)
    cadena.decir("siéntate")
    assert cadena.comandos == ["ksit"]


def test_h1_perro_solo_sin_orden_vuelve_a_la_escucha_normal(cadena):
    """REQ-35: ningún comando, y la siguiente orden con nombre se atiende."""
    cadena.decir("Perro")
    cadena.esperar(cadena.ajustes.espera_orden_s + 1)
    cadena.decir("siéntate")
    assert cadena.comandos == []
    cadena.decir("Perro, siéntate")
    assert cadena.comandos == ["ksit"]


# ------------------------------------------------------------------ Historia 2


def test_h2_20_entradas_sin_sentido_ningun_comando_y_aviso_cada_vez(cadena):
    """REQ-12, SC-005, ESC-04."""
    frases = leer_frases("sin_sentido.txt")
    assert len(frases) == 20
    for frase in frases:
        cadena.decir(frase)
    assert cadena.comandos == []
    assert cadena.avisos == [AVISO_NO_ENTENDIDA] * 20


def test_h2_10_ordenes_fuera_del_catalogo_ningun_comando_y_aviso_cada_vez(cadena):
    """REQ-13, ESC-05."""
    frases = leer_frases("fuera_catalogo.txt")
    assert len(frases) == 10
    for frase in frases:
        cadena.decir(frase)
    assert cadena.comandos == []
    assert len(cadena.avisos) == 10
    assert all(a.startswith(AVISO_NO_DISPONIBLE) for a in cadena.avisos)


def test_h2_orden_valida_tras_20_entradas_invalidas(cadena):
    """REQ-23, SC-006."""
    for frase in leer_frases("sin_sentido.txt"):
        cadena.decir(frase)
    cadena.decir("Perro, levántate")
    assert cadena.comandos == ["kup"]


# ------------------------------------------------------------------ Historia 3


def test_h3_el_simulado_registra_la_cadena_exacta_y_la_hora(cadena):
    """REQ-20, REQ-26: sin robot ni puerto serie."""
    cadena.esperar(1.0)
    cadena.decir("Perro, siéntate")
    assert cadena.robot.registro == [(pytest.approx(1.0), "ksit")]


# ------------------------------------------------------------------ Historia 4


@pytest.mark.parametrize("frase", leer_frases("encadenadas.txt"))
def test_h4_frases_encadenadas_llegan_en_el_orden_dicho(cadena, frase):
    """REQ-29, SC-009 (2 y 3 órdenes)."""
    texto, _, ids = (p.strip() for p in frase.partition("=>"))
    esperado = [c for i in ids.split(",") for c in comando_de(cadena.catalogo, i.strip())]
    cadena.decir(texto)
    assert cadena.comandos == esperado[:1]  # la segunda espera a que termine la primera
    cadena.esperar(10.0)
    assert cadena.comandos == esperado


def test_h4_cada_comando_sale_al_terminar_el_anterior(cadena):
    """REQ-29, ESC-10: kwkF (duración de prueba) y después ksit."""
    cadena.decir("Perro, camina y siéntate")
    cadena.esperar(DURACION_PRUEBA_S - 0.25)
    assert cadena.comandos == ["kwkF"]
    cadena.esperar(0.25)
    assert [c for _, c in cadena.robot.registro] == ["kwkF", "ksit"]
    assert cadena.robot.registro[1][0] == pytest.approx(DURACION_PRUEBA_S)


def test_h4_orden_fuera_del_catalogo_se_salta_con_aviso(cadena):
    """REQ-29, escenario 2, SC-009."""
    cadena.decir("Perro, camina y bailoteo y siéntate")
    cadena.esperar(5.0)
    assert cadena.comandos == ["kwkF", "ksit"]
    assert any("bailoteo" in a for a in cadena.avisos)


def test_h4_tres_ordenes_con_robot_ocupado_en_orden_de_llegada(catalogo):
    """REQ-32, SC-010, ESC-06, en modo cola (nueva_orden_interrumpe = false)."""
    cadena = Cadena(con_duraciones_de_prueba(catalogo), interrumpe=False)
    cadena.decir("Perro, camina")
    cadena.esperar(0.25)
    cadena.decir("Perro, siéntate")
    cadena.decir("Perro, levántate")
    cadena.decir("Perro, saluda")
    assert cadena.comandos == ["kwkF"]
    cadena.esperar(10.0)
    assert cadena.comandos == ["kwkF", "ksit", "kup", "khi"]
    horas = [h for h, _ in cadena.robot.registro]
    assert horas == pytest.approx([0.0, 1.0, 3.0, 4.0])  # ksit dura 2 s (H1 §2.4), el resto valor de prueba


def test_h4_orden_nueva_interrumpe_la_anterior_y_se_ejecuta_ya(cadena):
    """Modo por defecto (nueva_orden_interrumpe = true): la última orden manda, sin esperar."""
    cadena.decir("Perro, camina")
    cadena.esperar(0.25)
    cadena.decir("Perro, siéntate")
    cadena.decir("Perro, saluda")
    assert cadena.robot.registro == [(0.0, "kwkF"), (0.25, "ksit"), (0.25, "khi")]
    assert cadena.gestor.cola == ()
    cadena.esperar(10.0)
    assert cadena.comandos == ["kwkF", "ksit", "khi"]


def test_h4_interrumpir_con_el_catalogo_real_no_se_atasca(catalogo):
    """Con las duraciones reales en null, la marcha no termina sola; la orden nueva la corta igualmente."""
    cadena = Cadena(catalogo)
    cadena.decir("Perro, camina")
    cadena.esperar(5.0)
    cadena.decir("Perro, siéntate")
    assert cadena.comandos == ["kwkF", "ksit"]


def test_h4_ordenes_de_una_misma_frase_siguen_en_orden(cadena):
    """Interrumpir afecta a lo anterior, no a las órdenes encadenadas de la frase nueva."""
    cadena.decir("Perro, camina")
    cadena.decir("Perro, siéntate y levántate")
    assert cadena.comandos == ["kwkF", "ksit"]
    cadena.esperar(3.0)
    assert cadena.comandos == ["kwkF", "ksit", "kup"]


# ------------------------------------------------------------------ Historia 5


def test_h5_para_con_accion_en_curso_envia_krest_y_no_queda_en_cola(cadena):
    """REQ-07, SC-012."""
    cadena.decir("Perro, camina")
    cadena.esperar(0.5)
    cadena.decir("Perro, para")
    assert cadena.robot.registro == [(0.0, "kwkF"), (pytest.approx(0.5), "krest")]
    assert cadena.gestor.cola == ()


@pytest.mark.discrepancia("OPEN-12")
def test_h5_para_con_ordenes_en_cola_las_descarta(catalogo):
    """D-10 opción A: «para» vacía la cola (modo cola: en el modo por defecto no se acumulan órdenes)."""
    cadena = Cadena(con_duraciones_de_prueba(catalogo), interrumpe=False)
    cadena.decir("Perro, camina y siéntate")
    cadena.decir("Perro, levántate")
    cadena.decir("Perro, para")
    cadena.esperar(10.0)
    assert cadena.comandos == ["kwkF", "krest"]


@pytest.mark.discrepancia("OPEN-12")
def test_h5_para_dentro_de_una_frase_descarta_el_resto(cadena):
    """Casos límite: «camina y para y siéntate» (D-10, P-04)."""
    cadena.decir("Perro, camina y para y siéntate")
    cadena.esperar(10.0)
    assert cadena.comandos == ["krest"]


@pytest.mark.discrepancia("Y-03")
def test_h5_parada_de_emergencia_completa(cadena):
    """REQ-30, SC-011: comando de parada, cola vacía, 10 órdenes sin comando, segundo clic."""
    cadena.decir("Perro, camina y siéntate y levántate")
    cadena.esperar(0.5)
    cadena.gestor.pulsar_parada()
    assert cadena.comandos == ["kwkF", cadena.ajustes.comando_parada]
    assert cadena.gestor.cola == ()
    for _ in range(10):
        cadena.decir("Perro, siéntate")
    cadena.esperar(5.0)
    assert cadena.comandos == ["kwkF", "d"]
    assert cadena.avisos.count(AVISO_PARADA_ACTIVA) == 11
    cadena.gestor.pulsar_parada()
    cadena.decir("Perro, siéntate")
    assert cadena.comandos == ["kwkF", "d", "ksit"]


# ------------------------------------------------------------------ Historia 6 (REQ-25, sin conexión)


def test_h6_sin_conexion_no_envia_y_avisa(catalogo):
    """REQ-25, ESC-07."""
    cadena = Cadena(con_duraciones_de_prueba(catalogo), conectado=False)
    cadena.decir("Perro, siéntate")
    assert cadena.comandos == []
    assert cadena.avisos == [AVISO_NO_CONECTADO]


# ------------------------------------------------------------------ Historia 7


def test_h7_reposo_tras_T_y_una_orden_lo_despierta(cadena):
    """REQ-31, ESC-03: comando de reposo sin aviso; la orden siguiente se ejecuta."""
    cadena.decir("Perro, siéntate")
    cadena.esperar(T_PRUEBA_S - 1)
    assert cadena.comandos == ["ksit"]
    cadena.esperar(1.0)
    assert cadena.comandos == ["ksit", cadena.ajustes.comando_reposo]
    assert cadena.gestor.estado is Estado.REPOSO
    assert cadena.avisos == []
    cadena.decir("Perro, levántate")
    assert cadena.comandos == ["ksit", "krest", "kup"]


def test_h7_low_power_avisa_de_cargar_el_robot(cadena):
    """REQ-33, ESC-08."""
    cadena.robot.inyectar_linea("Low power: 6.5V")
    cadena.esperar(0.25)
    assert cadena.avisos == [AVISO_BATERIA_BAJA]
    assert cadena.comandos == []


# ------------------------------------------------------------------ catálogo real: duraciones sin medir


@pytest.mark.pendiente("P-03")
def test_catalogo_real_marcha_sin_duracion_bloquea_la_cola_hasta_para(catalogo):
    """Con `kwkF` sin duración (null), «siéntate» espera; «para» corta la marcha y vacía la cola."""
    cadena = Cadena(catalogo)
    cadena.decir("Perro, camina y siéntate")
    cadena.esperar(10.0)
    assert cadena.comandos == ["kwkF"]
    cadena.decir("Perro, para")
    assert cadena.comandos == ["kwkF", "krest"]
    assert cadena.gestor.cola == ()
