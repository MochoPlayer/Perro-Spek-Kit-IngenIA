# Pruebas del enlace serie con puerto falso (loop://), sin hardware. Cubre REQ-20, REQ-33, REQ-34.
import serial

from atenio.enlace import EnlaceSerie, es_bateria_baja


def falso():
    return EnlaceSerie("loop://", 115200)


def test_conecta_y_desconecta():
    e = falso()
    assert not e.conectado
    assert e.conectar() and e.conectado
    e.desconectar()
    assert not e.conectado


def test_sin_puerto_no_conecta():
    assert EnlaceSerie(None).conectar() is False


def test_error_al_abrir_devuelve_false():
    def abrir(*a, **k):
        raise serial.SerialException("no existe")
    e = EnlaceSerie("COM99", abrir=abrir)
    assert e.conectar() is False and not e.conectado


def test_envia_cadena_con_fin_de_linea():
    e = falso()
    e.conectar()
    assert e.enviar("ksit")
    assert e._ser.read(10) == b"ksit\n"


def test_fin_de_linea_configurable():
    e = EnlaceSerie("loop://", fin_de_linea="\r\n")
    e.conectar()
    e.enviar("d")
    assert e._ser.read(10) == b"d\r\n"


def test_sin_conexion_envio_falso():
    assert falso().enviar("ksit") is False


def test_nunca_envia_giroscopio():
    e = falso()
    e.conectar()
    assert e.enviar("G") is False
    assert e.enviar("g") is False
    assert e._ser.read(10) == b""


def test_lee_lineas_completas_y_guarda_el_resto():
    e = falso()
    e.conectar()
    e._ser.write(b"Low power: 6.5V\r\nok\npar")
    assert e.leer_lineas() == ["Low power: 6.5V", "ok"]
    e._ser.write(b"cial\n")
    assert e.leer_lineas() == ["parcial"]
    assert e.leer_lineas() == []


def test_deteccion_bateria_baja():
    assert es_bateria_baja("Low power: 6.5V")
    assert es_bateria_baja("low power")
    assert not es_bateria_baja("ksit")


def test_fallo_de_escritura():
    e = falso()
    e.conectar()
    def mal(_):
        raise serial.SerialException("cable")
    e._ser.write = mal
    assert e.enviar("ksit") is False
