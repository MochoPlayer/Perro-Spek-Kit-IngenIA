# Pruebas del robot simulado. Cubre REQ-26, REQ-25, REQ-33, REQ-20, REQ-34.
from atenio.enlace import EnlaceSimulado, es_bateria_baja
from atenio.reloj import RelojSimulado


def hacer():
    r = RelojSimulado()
    return r, EnlaceSimulado(r)


def test_registra_hora_y_cadena_exacta():
    r, e = hacer()
    assert e.enviar("ksit")
    r.avanzar(2)
    assert e.enviar("kwkF")
    assert e.registro == [(0.0, "ksit"), (2.0, "kwkF")]


def test_sin_conexion_no_envia():
    _, e = hacer()
    e.simular_sin_conexion()
    assert not e.conectado
    assert e.enviar("ksit") is False
    assert e.registro == []
    assert e.conectar() and e.enviar("ksit")


def test_fallo_de_envio():
    _, e = hacer()
    e.fallo_envio = True
    assert e.enviar("ksit") is False
    assert e.registro == []


def test_inyecta_low_power_y_lo_detecta():
    _, e = hacer()
    e.inyectar_linea("Low power: 6.5V")
    e.inyectar_linea("otra")
    lineas = e.leer_lineas()
    assert [es_bateria_baja(l) for l in lineas] == [True, False]
    assert e.leer_lineas() == []


def test_rechaza_giroscopio():
    _, e = hacer()
    assert e.enviar("G") is False
    assert e.enviar("g") is False
    assert e.registro == []
