"""Pruebas del catálogo de órdenes (datos/catalogo.json, D-05).

Cubre REQ-02 a REQ-11 (comando exacto de spec.md, SC-002) y REQ-14 a REQ-16 (opcionales).
"""
from __future__ import annotations

import json

import pytest

from atenio.catalogo import Catalogo, ErrorCatalogo, cargar_catalogo, normalizar
from atenio.modelos import Orden, Paso

NIVEL_1 = {
    "REQ-02": ("siéntate", "ksit"),
    "REQ-03": ("levántate", "kup"),
    "REQ-04": ("camina", "kwkF"),
    "REQ-05": ("izquierda", "kwkL"),
    "REQ-06": ("derecha", "kwkR"),
    "REQ-07": ("para", "krest"),
    "REQ-08": ("túmbate", "d"),
    "REQ-09": ("saluda", "khi"),
    "REQ-10": ("equilíbrate", "kbalance"),
    "REQ-11": ("trota", "ktrF"),
}


def test_catalogo_tiene_las_10_ordenes_del_nivel_1_y_las_3_opcionales(catalogo):
    ids = {o.id for o in catalogo.ordenes}
    assert set(NIVEL_1) <= ids
    assert {"REQ-14", "REQ-15", "REQ-16"} <= ids
    assert len(catalogo) == 13


@pytest.mark.parametrize("id_orden", sorted(NIVEL_1))
def test_orden_del_nivel_1_tiene_la_palabra_y_el_comando_de_spec(catalogo, id_orden):
    palabra, comando = NIVEL_1[id_orden]
    orden = catalogo.por_id(id_orden)
    assert palabra in orden.palabras
    assert [p.comando for p in orden.pasos] == [comando]
    assert catalogo.buscar(palabra) is orden


def test_solo_para_interrumpe(catalogo):
    assert [o.id for o in catalogo.ordenes if o.interrumpe] == ["REQ-07"]


def test_sinonimos_de_opciones_ordenes_de_voz(catalogo):
    # Tier 1 y T2-13 de opciones-ordenes-de-voz.md; H1 §2.4: «arriba» = «levántate» = kup.
    assert catalogo.buscar("arriba").id == "REQ-03"
    assert catalogo.buscar("adelante").id == "REQ-04"
    assert catalogo.buscar("stop").id == "REQ-07"
    assert catalogo.buscar("descansa").id == "REQ-08"
    assert catalogo.buscar("sentado").id == "REQ-02"
    assert catalogo.buscar("a sentarse").id == "REQ-02"


def test_busqueda_sin_tildes_ni_mayusculas(catalogo):
    assert catalogo.buscar("SIENTATE").id == "REQ-02"
    assert catalogo.buscar("Equilibrate").id == "REQ-10"
    assert catalogo.buscar("sígueme") is None


def test_duracion_provisional_de_ksit_y_el_resto_sin_dato(catalogo):
    # H1 §2.4 da «2 s para ksit» como único ejemplo; el resto está por medir (I-4, T069).
    assert catalogo.por_id("REQ-02").pasos == (Paso("ksit", 2.0),)
    sin_dato = [o.id for o in catalogo.ordenes for p in o.pasos if p.duracion_s is None]
    assert "REQ-02" not in sin_dato
    assert "REQ-04" in sin_dato


def test_json_marca_cada_paso_como_provisional_y_con_fuente():
    from atenio.catalogo import RUTA_POR_DEFECTO

    datos = json.loads(RUTA_POR_DEFECTO.read_text(encoding="utf-8"))
    for orden in datos["ordenes"]:
        for paso in orden["pasos"]:
            assert paso["provisional"] is True, orden["id"]
            assert paso["fuente"], orden["id"]


@pytest.mark.pendiente("P-09")
def test_opcionales_de_nivel_2(catalogo):
    assert catalogo.por_id("REQ-14").pasos == ()  # secuencia de «baila» sin definir (OPEN-08)
    assert [p.comando for p in catalogo.por_id("REQ-15").pasos] == ["kwkL"]
    assert [p.comando for p in catalogo.por_id("REQ-16").pasos] == ["kwkL", "kwkL"]  # dos giros seguidos


def test_todos_los_comandos_estan_en_la_lista_segura(catalogo):
    # comandos-bittle-estandar-seguros.md: los del Nivel 1 están todos en la lista (kwkR como espejo, d como token).
    permitidos = {"ksit", "kup", "kwkF", "kwkL", "kwkR", "krest", "d", "khi", "kbalance", "ktrF"}
    usados = {p.comando for o in catalogo.ordenes for p in o.pasos}
    assert usados <= permitidos


def test_normalizar():
    assert normalizar("¡Perro, SIÉNTATE!") == "perro sientate"
    assert normalizar("  da   una\tvuelta ") == "da una vuelta"
    assert normalizar("mañana") == "mañana"
    assert normalizar("pingüino") == "pinguino"


def test_palabra_repetida_en_dos_ordenes_es_un_error():
    a = Orden("REQ-90", ("hola",), (Paso("khi", None),))
    b = Orden("REQ-91", ("Holá",), (Paso("kup", None),))
    with pytest.raises(ErrorCatalogo):
        Catalogo([a, b])


def test_id_repetido_es_un_error():
    a = Orden("REQ-90", ("uno",), (Paso("khi", None),))
    b = Orden("REQ-90", ("dos",), (Paso("kup", None),))
    with pytest.raises(ErrorCatalogo):
        Catalogo([a, b])


def test_cargar_catalogo_de_otro_fichero(tmp_path):
    ruta = tmp_path / "catalogo.json"
    ruta.write_text(
        json.dumps({"ordenes": [{"id": "REQ-99", "palabras": ["choca"], "pasos": [{"comando": "kfiv", "duracion_s": 1}]}]}),
        encoding="utf-8",
    )
    cat = cargar_catalogo(ruta)
    assert cat.buscar("choca").pasos == (Paso("kfiv", 1.0),)


def test_cargar_catalogo_sin_lista_de_ordenes_es_un_error(tmp_path):
    ruta = tmp_path / "malo.json"
    ruta.write_text("{}", encoding="utf-8")
    with pytest.raises(ErrorCatalogo):
        cargar_catalogo(ruta)
