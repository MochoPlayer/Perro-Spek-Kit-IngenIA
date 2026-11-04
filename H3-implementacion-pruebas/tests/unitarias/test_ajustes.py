# Pruebas de la carga de ajustes. Cubre REQ-31, REQ-35, OPEN-11.
import json

import pytest

from atenio.ajustes import cargar_ajustes


def test_valores_de_plan():
    a = cargar_ajustes()
    assert a.espera_orden_s == 5
    assert a.inactividad_demo_s == 5 * 60
    assert a.inactividad_real_s == 15 * 60
    assert a.comando_reposo == "krest"
    assert a.comando_parada == "d"
    assert a.baudios == 115200
    assert a.para_vacia_cola is True


def test_valores_sin_dato_son_null_y_provisionales():
    a = cargar_ajustes()
    assert a.puerto is None
    assert a.max_ordenes_por_frase is None
    assert {"puerto", "max_ordenes_por_frase", "baudios", "espera_orden_s"} <= set(a.provisionales)


def test_cada_valor_tiene_fuente():
    with open(__import__("atenio.ajustes", fromlist=["x"]).RUTA_POR_DEFECTO, encoding="utf-8") as f:
        datos = json.load(f)
    for clave, e in datos.items():
        assert e.get("fuente"), clave
        assert "provisional" in e, clave


@pytest.mark.discrepancia("X-02")
def test_baudios_provisionales_por_discrepancia():
    assert "baudios" in cargar_ajustes().provisionales


@pytest.mark.discrepancia("OPEN-12")
def test_para_vacia_la_cola_es_ajuste_provisional():
    assert "para_vacia_cola" in cargar_ajustes().provisionales


def test_ruta_propia(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({k: {"valor": v} for k, v in {
        "espera_orden_s": 1, "inactividad_demo_s": 2, "inactividad_real_s": 3,
        "comando_reposo": "x", "comando_parada": "y", "puerto": "COM9", "baudios": 9600,
        "max_ordenes_por_frase": 3, "para_vacia_cola": False, "fin_de_linea": "\r\n"}.items()}),
        encoding="utf-8")
    a = cargar_ajustes(f)
    assert (a.puerto, a.baudios, a.max_ordenes_por_frase, a.provisionales) == ("COM9", 9600, 3, ())


def test_palabra_de_activacion_es_un_ajuste():
    # Mario, 04/11: «Perro» en lugar de «Atenio» (discrepancias.md, Z-01). Sin la clave: «perro».
    a = cargar_ajustes()
    assert a.palabra_activacion == "perro"
    assert "palabra_activacion" in a.provisionales
    assert a.voz["pista"] == "Perro"
