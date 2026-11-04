# Enlace por puerto serie real con pyserial (D-04). Cubre REQ-20, REQ-33, REQ-34 (D-12).
import threading
import time

import serial

from .base import cadena_prohibida


LISTO = "ready!"  # el Bittle lo escribe al terminar de arrancar (prueba de conexión del 04/11)


class EnlaceSerie:
    def __init__(self, puerto: str | None, baudios: int = 115200, fin_de_linea: str = "\n",
                 abrir=serial.serial_for_url, *, espera_arranque_s: float = 0.0,
                 tope_abrir_s: float | None = None, ahora=time.monotonic, dormir=time.sleep) -> None:
        self._puerto = puerto
        self._baudios = baudios
        self._fin = fin_de_linea
        self._abrir = abrir  # sustituible en pruebas
        self._espera_arranque_s = espera_arranque_s
        self._tope_abrir_s = tope_abrir_s  # None: sin tope (abrir puede bloquear si el Bluetooth no responde)
        self.error: str | None = None  # por qué falló el último conectar(), para mostrarlo
        self._ahora = ahora
        self._dormir = dormir
        self._ser = None
        self._resto = ""
        self.arranque: list[str] = []  # lo que escribió el robot al arrancar (versión de firmware, etc.)

    @property
    def puerto(self) -> str | None:
        return self._puerto

    @property
    def conectado(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def conectar(self) -> bool:
        self.error = None
        if not self._puerto:
            self.error = "no hay puerto (ajustes.json o --com)"
            return False
        try:
            self._ser = self._abrir_con_tope()
        except (serial.SerialException, OSError, ValueError) as e:
            self._ser = None
            self.error = str(e)
            return False
        if self._ser is None:
            self.error = (f"{self._puerto} no responde tras {self._tope_abrir_s:g} s: "
                          "¿robot encendido y emparejado por Bluetooth?")
            return False
        if self.conectado and self._espera_arranque_s > 0:
            self._esperar_listo()
        return self.conectado

    def _abrir_con_tope(self):
        """Abre el puerto. En Windows, abrir un COM de Bluetooth sin el robot encendido bloquea sin límite
        (visto el 04/11): con `tope_abrir_s` se abre en un hilo y, si no termina a tiempo, se devuelve None.
        """
        if self._tope_abrir_s is None:
            return self._abrir(self._puerto, self._baudios, timeout=0)
        resultado: dict = {}
        cerrojo = threading.Lock()
        abandonado = threading.Event()

        def tarea():
            try:
                ser = self._abrir(self._puerto, self._baudios, timeout=0)
            except Exception as e:  # se relanza en el hilo principal
                resultado["error"] = e
                return
            with cerrojo:
                if abandonado.is_set():  # llegó tarde: nadie lo usará
                    ser.close()
                else:
                    resultado["ser"] = ser

        hilo = threading.Thread(target=tarea, name="atenio-abrir-puerto", daemon=True)
        hilo.start()
        hilo.join(self._tope_abrir_s)
        with cerrojo:
            if "ser" not in resultado and "error" not in resultado:
                abandonado.set()
                return None
        if "error" in resultado:
            raise resultado["error"]
        return resultado["ser"]

    def _esperar_listo(self) -> None:
        """Al abrir el puerto el Bittle se reinicia: se leen sus líneas hasta «Ready!» o hasta el tope.

        Si el robot no se reinicia (no dice nada), se espera el tope entero y se sigue: no es un error.
        """
        self.arranque = []
        limite = self._ahora() + self._espera_arranque_s
        while self.conectado and self._ahora() < limite:
            lineas = self.leer_lineas()
            self.arranque.extend(lineas)
            if any(l.strip().lower() == LISTO for l in lineas):
                self._dormir(0.5)  # tras «Ready!» el robot aún escribe una o dos líneas
                self.arranque.extend(self.leer_lineas())
                return
            self._dormir(0.05)

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
            # Cable quitado o Bluetooth caído: se marca desconectado para que el gestor lo publique (T060).
            self.desconectar()
            return []
        # El módulo Bluetooth del Bittle envía bytes 0 sueltos (visto en la sesión del 04/11): se descartan.
        texto = self._resto + datos.replace(b"\x00", b"").decode("ascii", errors="replace")
        *lineas, self._resto = texto.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return [l for l in lineas if l.strip()]
