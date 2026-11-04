"""Pruebas del intérprete con frases de texto (D-09), sin robot ni micrófono.

Cubre REQ-01, REQ-02 a REQ-16, REQ-12, REQ-13, REQ-18, REQ-23, REQ-29 y REQ-35.
"""
from __future__ import annotations

import pytest

from atenio.interprete import AVISO_NO_ENTENDIDA, Interprete
from atenio.modelos import TipoInterpretacion as T
from conftest import leer_frases


def _con_resultado(nombre: str) -> list[tuple[str, list[str]]]:
    filas = []
    for linea in leer_frases(nombre):
        frase, ids = linea.split("=>")
        filas.append((frase.strip(), [i.strip() for i in ids.split(",")]))
    return filas


@pytest.fixture
def interprete(catalogo, reloj):
    return Interprete(catalogo, reloj=reloj)


def ids(interpretacion) -> list[str]:
    return [o.id for o in interpretacion.ordenes]


# ---------------------------------------------------------------- REQ-01: activación


def test_hay_20_frases_con_nombre_y_20_sin_nombre():
    assert len(leer_frases("con_nombre.txt")) == 20
    assert len(leer_frases("sin_nombre.txt")) == 20


@pytest.mark.parametrize("frase,esperado", _con_resultado("con_nombre.txt"))
def test_req01_frase_con_nombre_es_orden(interprete, frase, esperado):
    r = interprete.interpretar(frase)
    assert r.tipo is T.ORDENES
    assert ids(r) == esperado
    assert r.avisos == ()


@pytest.mark.parametrize("frase", leer_frases("sin_nombre.txt"))
def test_req01_frase_sin_nombre_se_ignora(interprete, frase):
    r = interprete.interpretar(frase)
    assert r.tipo is T.IGNORADA
    assert r.ordenes == ()
    assert r.avisos == ()  # sin «Perro» no se avisa (contrato de plan.md)


def test_req01_perro_debe_ir_al_principio(interprete):
    assert interprete.interpretar("siéntate Perro").tipo is T.IGNORADA
    assert interprete.interpretar("oye Perro siéntate").tipo is T.IGNORADA


def test_req18_normalizacion_da_el_mismo_resultado(interprete):
    # tasks.md T013: «Perro, siéntate» y «perro sientate» dan lo mismo.
    assert interprete.interpretar("Perro, siéntate") == interprete.interpretar("perro sientate")


@pytest.mark.parametrize(
    "orden,comandos",
    [
        ("siéntate", ["ksit"]),
        ("levántate", ["kup"]),
        ("camina", ["kwkF"]),
        ("izquierda", ["kwkL"]),
        ("derecha", ["kwkR"]),
        ("para", ["krest"]),
        ("túmbate", ["d"]),
        ("saluda", ["khi"]),
        ("equilíbrate", ["kbalance"]),
        ("trota", ["ktrF"]),
        ("media vuelta", ["kwkL"]),
        ("da una vuelta", ["kwkL", "kwkL"]),
    ],
)
def test_req02_a_req16_texto_da_los_comandos_del_catalogo(interprete, orden, comandos):
    r = interprete.interpretar(f"Perro, {orden}")
    assert r.tipo is T.ORDENES
    assert [p.comando for o in r.ordenes for p in o.pasos] == comandos


def test_req07_para_marca_interrumpe(interprete):
    r = interprete.interpretar("Perro, para")
    assert r.ordenes[0].interrumpe is True


# ---------------------------------------------------------------- REQ-12 y REQ-13: entradas no válidas


def test_hay_20_sin_sentido_y_10_fuera_del_catalogo():
    assert len(leer_frases("sin_sentido.txt")) == 20
    assert len(leer_frases("fuera_catalogo.txt")) == 10


@pytest.mark.discrepancia("Y-02")
@pytest.mark.parametrize("frase", leer_frases("sin_sentido.txt"))
def test_req12_sin_sentido_no_entendida_con_aviso(interprete, frase):
    r = interprete.interpretar(frase)
    assert r.tipo is T.NO_ENTENDIDA
    assert r.ordenes == ()
    assert AVISO_NO_ENTENDIDA in r.avisos


@pytest.mark.discrepancia("Y-02")
@pytest.mark.parametrize("frase", ["", "   ", "ruido ruido ruido", "shhhhh", "1 2 3 4"])
def test_req12_ruido_sin_perro_se_ignora_sin_aviso(interprete, frase):
    # Y-02 opción 1: sin «Perro» se ignora todo, ruido incluido (sigue el contrato de plan.md).
    r = interprete.interpretar(frase)
    assert r.tipo is T.IGNORADA
    assert r.avisos == ()


@pytest.mark.discrepancia("Y-02")
@pytest.mark.parametrize("frase", leer_frases("fuera_catalogo.txt"))
def test_req13_fuera_del_catalogo_con_aviso(interprete, frase):
    r = interprete.interpretar(frase)
    assert r.tipo is T.FUERA_DEL_CATALOGO
    assert r.ordenes == ()
    assert len(r.avisos) == 1
    assert r.avisos[0].startswith("orden no disponible")


def test_req13_sigueme_da_aviso_de_orden_no_disponible(interprete):
    r = interprete.interpretar("Perro, sígueme")
    assert r.avisos == ("orden no disponible: «sigueme»",)


@pytest.mark.pendiente("P-09")
def test_req14_baila_sin_secuencia_es_orden_no_disponible(interprete):
    # La secuencia de «baila» no está definida (OPEN-08): sin pasos no se envía nada.
    r = interprete.interpretar("Perro, baila")
    assert r.tipo is T.FUERA_DEL_CATALOGO
    assert r.avisos == ("orden no disponible: «baila»",)


def test_req23_sigue_funcionando_tras_20_entradas_invalidas(interprete):
    invalidas = (leer_frases("sin_sentido.txt") + leer_frases("fuera_catalogo.txt"))[:20]
    for frase in invalidas:
        assert interprete.interpretar(frase).tipo in (T.NO_ENTENDIDA, T.FUERA_DEL_CATALOGO)
    r = interprete.interpretar("Perro, siéntate")
    assert r.tipo is T.ORDENES and ids(r) == ["REQ-02"]


# ---------------------------------------------------------------- REQ-29: órdenes encadenadas


@pytest.mark.pendiente("P-03")
@pytest.mark.parametrize("frase,esperado", _con_resultado("encadenadas.txt"))
def test_req29_encadenadas_en_el_orden_dicho(interprete, frase, esperado):
    r = interprete.interpretar(frase)
    assert r.tipo is T.ORDENES
    assert ids(r) == esperado


@pytest.mark.pendiente("P-03")
def test_req29_orden_fuera_del_catalogo_se_salta_con_aviso(interprete):
    r = interprete.interpretar("Perro, camina y bailoteo y siéntate")
    assert ids(r) == ["REQ-04", "REQ-02"]
    assert r.avisos == ("orden no disponible: «bailoteo»",)


@pytest.mark.pendiente("P-03")
def test_req29_todas_fuera_del_catalogo(interprete):
    r = interprete.interpretar("Perro, salta y corre")
    assert r.tipo is T.FUERA_DEL_CATALOGO
    assert len(r.avisos) == 2


@pytest.mark.pendiente("P-03")
def test_req29_palabras_de_enlace_sin_ordenes(interprete):
    r = interprete.interpretar("Perro, y luego")
    assert r.tipo is T.NO_ENTENDIDA


@pytest.mark.pendiente("P-03")
@pytest.mark.parametrize("maximo", [2, 3])
def test_req29_maximo_de_ordenes_por_frase(catalogo, maximo):
    interprete = Interprete(catalogo, max_ordenes=maximo)
    r = interprete.interpretar("Perro, levántate y camina y izquierda y siéntate")
    assert ids(r) == ["REQ-03", "REQ-04", "REQ-05", "REQ-02"][:maximo]
    assert len(r.avisos) == 4 - maximo


def test_palabras_de_enlace_configurables(catalogo):
    interprete = Interprete(catalogo, palabras_enlace=("y", "luego", "después"))
    assert ids(interprete.interpretar("Perro, camina después siéntate")) == ["REQ-04", "REQ-02"]


# ---------------------------------------------------------------- D-10: «para» en una frase encadenada


@pytest.mark.pendiente("P-04")
def test_d10_camina_y_para(interprete):
    r = interprete.interpretar("Perro camina y para")
    assert r.tipo is T.ORDENES
    assert ids(r) == ["REQ-04", "REQ-07"]
    assert r.ordenes[-1].interrumpe
    assert r.avisos == ()


@pytest.mark.pendiente("P-04")
def test_d10_para_descarta_el_resto_de_la_frase(interprete):
    r = interprete.interpretar("Perro, siéntate y para y camina y saluda")
    assert ids(r) == ["REQ-02", "REQ-07"]
    assert r.avisos == ("«para» descarta el resto de la frase: «camina», «saluda»",)


@pytest.mark.pendiente("P-04")
def test_d10_opcion_c_para_en_su_posicion(catalogo):
    interprete = Interprete(catalogo, para_descarta_resto=False)
    assert ids(interprete.interpretar("Perro, siéntate y para y camina")) == ["REQ-02", "REQ-07", "REQ-04"]


# ---------------------------------------------------------------- REQ-35: «Perro» solo y espera de 5 s


def test_req35_solo_perro(interprete):
    r = interprete.interpretar("Perro")
    assert r.tipo is T.SOLO_ACTIVACION
    assert r.ordenes == ()
    assert interprete.esperando_orden


def test_req35_orden_sin_nombre_dentro_de_5_s(interprete, reloj):
    interprete.interpretar("¡Perro!")
    reloj.avanzar(3.0)
    r = interprete.interpretar("siéntate")
    assert r.tipo is T.ORDENES and ids(r) == ["REQ-02"]
    assert not interprete.esperando_orden


def test_req35_justo_a_los_5_s_todavia_vale(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(5.0)
    assert interprete.interpretar("camina").tipo is T.ORDENES


def test_req35_despues_de_5_s_se_ignora(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(5.01)
    assert interprete.interpretar("siéntate").tipo is T.IGNORADA
    assert not interprete.esperando_orden


def test_req35_la_espera_vale_solo_para_una_frase(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(1)
    assert interprete.interpretar("siéntate").tipo is T.ORDENES
    reloj.avanzar(1)
    assert interprete.interpretar("levántate").tipo is T.IGNORADA


def test_req35_sin_orden_la_siguiente_con_nombre_se_atiende(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(60)
    r = interprete.interpretar("Perro, levántate")
    assert r.tipo is T.ORDENES and ids(r) == ["REQ-03"]


def test_req35_encadenadas_dentro_de_la_espera(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(2)
    assert ids(interprete.interpretar("camina y siéntate")) == ["REQ-04", "REQ-02"]


@pytest.mark.discrepancia("Y-02")
def test_req35_frase_no_valida_dentro_de_la_espera_avisa(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(1)
    r = interprete.interpretar("sígueme")
    assert r.tipo is T.FUERA_DEL_CATALOGO
    assert not interprete.esperando_orden


def test_req35_perro_otra_vez_reinicia_la_espera(interprete, reloj):
    interprete.interpretar("Perro")
    reloj.avanzar(4)
    interprete.interpretar("Perro")
    reloj.avanzar(4)
    assert interprete.interpretar("saluda").tipo is T.ORDENES


def test_req35_espera_configurable_y_hora_por_parametro(catalogo):
    interprete = Interprete(catalogo, espera_s=2.0)  # sin reloj: la hora llega por `ahora`
    interprete.interpretar("Perro", ahora=100.0)
    assert interprete.interpretar("siéntate", ahora=103.0).tipo is T.IGNORADA


def test_req35_sin_hora_ni_reloj_es_un_error(catalogo):
    with pytest.raises(ValueError):
        Interprete(catalogo).interpretar("Perro")


def test_sin_reloj_las_frases_con_nombre_funcionan(catalogo):
    assert Interprete(catalogo).interpretar("Perro, siéntate").tipo is T.ORDENES


# ---------------------------------------------------------------- palabra de activación como ajuste (Z-01)


def test_el_nombre_anterior_atenio_ya_no_activa(interprete):
    assert interprete.interpretar("Atenio, siéntate").tipo is T.IGNORADA


def test_otra_palabra_de_activacion_se_compara_sin_tildes(catalogo, reloj):
    otro = Interprete(catalogo, reloj=reloj, palabras_activacion=("Bíttle",))
    assert ids(otro.interpretar("bittle, siéntate")) == ["REQ-02"]
    assert otro.interpretar("Perro, siéntate").tipo is T.IGNORADA
