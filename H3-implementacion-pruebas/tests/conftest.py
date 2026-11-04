"""Fixtures comunes de las pruebas de H3: catálogo, reloj falso y lectura de frases de tests/frases/.

Sin robot, sin micrófono y sin esperas reales (REQ-26, D-08, D-09).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from atenio.catalogo import Catalogo, cargar_catalogo

CARPETA_FRASES = Path(__file__).parent / "frases"


def leer_frases(nombre: str) -> list[str]:
    """Lee un fichero de tests/frases/: una frase por línea; «#» empieza un comentario."""
    lineas = (CARPETA_FRASES / nombre).read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.lstrip().startswith("#")]


class RelojFalso:
    """Reloj mínimo para las pruebas del intérprete. No sustituye a atenio.reloj.RelojSimulado."""

    def __init__(self, inicio: float = 0.0):
        self._t = inicio

    def ahora(self) -> float:
        return self._t

    def avanzar(self, s: float) -> None:
        self._t += s


@pytest.fixture(scope="session")
def catalogo() -> Catalogo:
    return cargar_catalogo()


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()
