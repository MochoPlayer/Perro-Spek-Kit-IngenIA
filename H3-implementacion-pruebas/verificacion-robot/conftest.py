"""Pruebas de las herramientas de verificación (no del programa). Se ejecutan aparte:

    python -m pytest verificacion-robot       (desde H3-implementacion-pruebas/)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # medicion.py, panel_robot.py

from atenio.reloj import RelojSimulado  # noqa: E402


@pytest.fixture
def reloj() -> RelojSimulado:
    return RelojSimulado()
