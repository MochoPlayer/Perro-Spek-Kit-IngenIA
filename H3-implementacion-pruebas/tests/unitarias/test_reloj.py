# Pruebas del reloj sustituible (D-08). Cubre REQ-26, REQ-31, REQ-35.
import pytest

from atenio.reloj import RelojReal, RelojSimulado


def test_simulado_empieza_en_cero_y_avanza():
    r = RelojSimulado()
    assert r.ahora() == 0.0
    r.avanzar(5)
    r.avanzar(0.5)
    assert r.ahora() == 5.5


def test_simulado_no_retrocede():
    with pytest.raises(ValueError):
        RelojSimulado().avanzar(-1)


def test_real_es_monotono():
    r = RelojReal()
    a = r.ahora()
    assert r.ahora() >= a
