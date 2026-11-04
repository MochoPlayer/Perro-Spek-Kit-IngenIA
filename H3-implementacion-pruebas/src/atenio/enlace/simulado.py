# Robot simulado con registro (D-03). Cubre REQ-26, REQ-25, REQ-33, REQ-20.
from ..reloj import Reloj
from .base import cadena_prohibida


class EnlaceSimulado:
    def __init__(self, reloj: Reloj, conectado: bool = True) -> None:
        self._reloj = reloj
        self._conectado = conectado
        self.fallo_envio = False
        self.registro: list[tuple[float, str]] = []
        self._entrada: list[str] = []

    @property
    def conectado(self) -> bool:
        return self._conectado

    def conectar(self) -> bool:
        self._conectado = True
        return True

    def desconectar(self) -> None:
        self._conectado = False

    def enviar(self, cadena: str) -> bool:
        if not self._conectado or self.fallo_envio or cadena_prohibida(cadena):
            return False
        self.registro.append((self._reloj.ahora(), cadena))
        return True

    def leer_lineas(self) -> list[str]:
        lineas, self._entrada = self._entrada, []
        return lineas

    # --- control para las pruebas ---
    def simular_sin_conexion(self) -> None:
        self._conectado = False

    def inyectar_linea(self, linea: str) -> None:
        self._entrada.append(linea)

    @property
    def cadenas(self) -> list[str]:
        return [c for _, c in self.registro]
