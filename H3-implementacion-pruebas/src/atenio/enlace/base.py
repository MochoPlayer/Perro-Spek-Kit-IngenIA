# Interfaz única del enlace con el robot (D-03) y detección de batería baja. Cubre REQ-20, REQ-33, REQ-34.
from typing import Protocol


class Enlace(Protocol):
    @property
    def conectado(self) -> bool: ...
    def conectar(self) -> bool: ...
    def desconectar(self) -> None: ...
    def enviar(self, cadena: str) -> bool: ...  # False si falla o no hay conexión
    def leer_lineas(self) -> list[str]: ...  # líneas recibidas desde la última lectura


def es_bateria_baja(linea: str) -> bool:
    """True si la línea del robot es el aviso «Low power» (REQ-33)."""
    return "low power" in linea.lower()


def cadena_prohibida(cadena: str) -> bool:
    """True si la cadena es el token de giroscopio G o g (REQ-34, D-12), solo o con argumentos."""
    c = cadena.strip()
    return bool(c) and c[0] in ("G", "g")
