"""Pruebas del servidor de la interfaz (T056) sin navegador: peticiones HTTP a un puerto libre de 127.0.0.1.

Cubre REQ-19 (lo que muestra la página) y REQ-30 (botón de parada). Robot simulado; no sale nada a la red.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from atenio.ajustes import cargar_ajustes
from atenio.enlace.simulado import EnlaceSimulado
from atenio.interfaz import crear_servidor, servir_en_hilo
from atenio.principal import Sistema
from atenio.reloj import RelojSimulado


@pytest.fixture
def web(catalogo):
    reloj = RelojSimulado()
    robot = EnlaceSimulado(reloj)
    sistema = Sistema(robot, reloj, catalogo=catalogo)
    sistema.arrancar(con_bucle=False)
    servidor = crear_servidor(sistema, 0)
    servir_en_hilo(servidor)
    base = f"http://127.0.0.1:{servidor.server_address[1]}"
    yield base, sistema, robot
    servidor.shutdown()
    servidor.server_close()


def pedir(url: str, datos: dict | None = None, metodo: str | None = None):
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    req = urllib.request.Request(url, data=cuerpo, method=metodo or ("POST" if cuerpo else "GET"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def test_solo_escucha_en_127_0_0_1(web):
    _, sistema, _ = web
    servidor = crear_servidor(sistema, 0)
    try:
        assert servidor.server_address[0] == "127.0.0.1"
    finally:
        servidor.server_close()


def test_la_pagina_tiene_los_elementos_y_no_usa_recursos_externos(web):
    base, _, _ = web
    estado, tipo, cuerpo = pedir(base + "/")
    html = cuerpo.decode("utf-8")
    assert estado == 200 and tipo.startswith("text/html")
    for id_ in ('id="texto"', 'id="orden"', 'id="conexion"', 'id="gestor"', 'id="avisos"',
                'id="registro"', 'id="parada"', 'id="frase"', 'id="voz"'):
        assert id_ in html
    assert "http://" not in html and "https://" not in html  # funciona sin internet


def test_una_frase_escrita_llega_al_registro_del_simulado(web):
    base, _, robot = web
    estado, _, _ = pedir(base + "/frase", {"texto": "Atenio, siéntate"})
    assert estado == 200
    assert robot.cadenas == ["ksit"]
    foto = json.loads(pedir(base + "/estado")[2])
    tipos = [e["tipo"] for e in foto["eventos"]]
    assert tipos == ["estado_conexion", "texto_reconocido", "orden_interpretada"]
    assert foto["registro"][-1]["comando"] == "ksit"
    assert foto["conectado"] is True and foto["estado"] == "Ocupado"


def test_estado_desde_devuelve_solo_lo_nuevo(web):
    base, _, _ = web
    primero = json.loads(pedir(base + "/estado")[2])
    pedir(base + "/frase", {"texto": "Atenio, 3 4 5 6 7 8 9 10"})
    nuevo = json.loads(pedir(base + f"/estado?desde={primero['total_eventos']}")[2])
    assert [e["tipo"] for e in nuevo["eventos"]] == ["texto_reconocido", "aviso"]
    assert nuevo["eventos"][1]["texto"] == "no se ha entendido bien"


def test_el_boton_activa_y_desactiva_la_parada(web):
    """REQ-30: un clic activa (envía el comando de parada y bloquea órdenes); otro clic desactiva."""
    base, _, robot = web
    r = json.loads(pedir(base + "/parada", metodo="POST")[2])
    assert r["parada"] is True
    assert robot.cadenas == [cargar_ajustes().comando_parada]
    pedir(base + "/frase", {"texto": "Atenio, siéntate"})
    assert robot.cadenas == [cargar_ajustes().comando_parada]  # bloqueada
    foto = json.loads(pedir(base + "/estado")[2])
    assert foto["estado"] == "Parada" and "parada de emergencia activa" in [e["texto"] for e in foto["eventos"]]
    r = json.loads(pedir(base + "/parada", metodo="POST")[2])
    assert r["parada"] is False
    pedir(base + "/frase", {"texto": "Atenio, siéntate"})
    assert robot.cadenas[-1] == "ksit"


@pytest.mark.parametrize("cuerpo", [b"no es json", b'{"texto": 5}'])
def test_frase_mal_formada_da_400(web, cuerpo):
    base, _, robot = web
    req = urllib.request.Request(base + "/frase", data=cuerpo, method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=5)
    assert e.value.code == 400
    assert robot.cadenas == []


def test_ruta_desconocida_da_404(web):
    base, _, _ = web
    with pytest.raises(urllib.error.HTTPError) as e:
        pedir(base + "/nada")
    assert e.value.code == 404
