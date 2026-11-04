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


def test_se_marca_desconectado_si_falla_la_lectura():
    """T060: cable quitado o Bluetooth caído; el gestor verá el cambio y lo publicará."""
    e = falso()
    e.conectar()
    def mal(_n):
        raise serial.SerialException("cable")
    e._ser.read = mal
    assert e.leer_lineas() == []
    assert not e.conectado


def test_descarta_los_bytes_cero_del_bluetooth():
    e = falso()
    e.conectar()
    e._ser.write(b"\x00\x00\x00k\x00\n\x00\x00")
    assert e.leer_lineas() == ["k"]
    e._ser.write(b"\n")
    assert e.leer_lineas() == []


class RelojFalso:
    """Reloj para la espera del arranque: cada «dormir» avanza el tiempo sin esperar de verdad."""

    def __init__(self):
        self.t = 0.0

    def ahora(self):
        return self.t

    def dormir(self, s):
        self.t += s


def test_espera_el_ready_del_robot_al_conectar():
    """Al abrir el puerto el Bittle se reinicia (prueba del 04/11) y escribe «Ready!» al acabar."""
    reloj = RelojFalso()
    e = EnlaceSerie("loop://", espera_arranque_s=8, ahora=reloj.ahora, dormir=reloj.dormir)
    real = e._abrir

    def abrir(*a, **k):
        ser = real(*a, **k)
        ser.write(b"* Start *\r\nBittle\r\nN_240517\r\nReady!\r\n")
        return ser

    e._abrir = abrir
    assert e.conectar()
    assert e.arranque[:4] == ["* Start *", "Bittle", "N_240517", "Ready!"]
    assert reloj.t < 8  # no ha agotado el tope
    assert e.leer_lineas() == []  # lo del arranque no llega luego al gestor


def test_si_el_robot_no_dice_ready_espera_el_tope_y_sigue():
    reloj = RelojFalso()
    e = EnlaceSerie("loop://", espera_arranque_s=2, ahora=reloj.ahora, dormir=reloj.dormir)
    assert e.conectar() and e.conectado
    assert reloj.t >= 2


def test_si_el_puerto_no_responde_se_rinde_al_tope():
    """Robot apagado: en Windows abrir el COM de Bluetooth no vuelve (04/11). El programa no se cuelga."""
    import threading

    soltar = threading.Event()

    def abrir_que_no_vuelve(*a, **k):
        soltar.wait(5)
        return serial.serial_for_url("loop://", timeout=0)

    e = EnlaceSerie("COM6", abrir=abrir_que_no_vuelve, tope_abrir_s=0.2)
    assert e.conectar() is False
    assert not e.conectado
    assert "no responde" in e.error
    soltar.set()  # si el puerto se abre tarde, se cierra solo y no se usa


def test_con_tope_el_puerto_que_responde_se_usa():
    e = EnlaceSerie("loop://", tope_abrir_s=2)
    assert e.conectar() and e.conectado and e.error is None


def test_con_tope_un_error_al_abrir_se_informa():
    def abrir(*a, **k):
        raise serial.SerialException("Acceso denegado")
    e = EnlaceSerie("COM6", abrir=abrir, tope_abrir_s=2)
    assert e.conectar() is False
    assert "Acceso denegado" in e.error


def test_sin_espera_no_lee_nada_al_conectar():
    e = EnlaceSerie("loop://")
    assert e.conectar()
    assert e.arranque == []


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
