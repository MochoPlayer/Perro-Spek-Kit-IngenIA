# Enlace por puerto serie real con pyserial (D-04). Cubre REQ-20, REQ-33, REQ-34 (D-12).
import serial

from .base import cadena_prohibida


class EnlaceSerie:
    def __init__(self, puerto: str | None, baudios: int = 115200, fin_de_linea: str = "\n",
                 abrir=serial.serial_for_url) -> None:
        self._puerto = puerto
        self._baudios = baudios
        self._fin = fin_de_linea
        self._abrir = abrir  # sustituible en pruebas
        self._ser = None
        self._resto = ""

    @property
    def conectado(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def conectar(self) -> bool:
        if not self._puerto:
            return False
        try:
            self._ser = self._abrir(self._puerto, self._baudios, timeout=0)
        except (serial.SerialException, OSError, ValueError):
            self._ser = None
            return False
        return self.conectado

    def desconectar(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def enviar(self, cadena: str) -> bool:
        if not self.conectado or cadena_prohibida(cadena):
            return False
        try:
            self._ser.write((cadena + self._fin).encode("ascii"))
            self._ser.flush()
        except (serial.SerialException, OSError, UnicodeEncodeError):
            return False
        return True

    def leer_lineas(self) -> list[str]:
        if not self.conectado:
            return []
        try:
            datos = self._ser.read(self._ser.in_waiting or 0)
        except (serial.SerialException, OSError):
            return []
        texto = self._resto + datos.decode("ascii", errors="replace")
        *lineas, self._resto = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return [l for l in lineas if l.strip()]
