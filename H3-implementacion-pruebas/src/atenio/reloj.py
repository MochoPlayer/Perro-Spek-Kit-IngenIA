# Reloj sustituible (D-08). Cubre REQ-26, REQ-31, REQ-35: las pruebas no esperan de verdad.
import time
from typing import Protocol


class Reloj(Protocol):
    def ahora(self) -> float: ...


class RelojReal:
    """Reloj monótono del sistema, en segundos."""

    def ahora(self) -> float:
        return time.monotonic()


class RelojSimulado:
    """Reloj que solo avanza cuando la prueba lo pide."""

    def __init__(self, inicio: float = 0.0) -> None:
        self._t = float(inicio)

    def ahora(self) -> float:
        return self._t

    def avanzar(self, s: float) -> None:
        if s < 0:
            raise ValueError("el reloj no puede retroceder")
        self._t += s
