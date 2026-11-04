"""Sinónimos y errores típicos del reconocedor para siéntate / levántate / para (REQ-02, REQ-03, REQ-07)."""
import pytest

from atenio.catalogo import cargar_catalogo, normalizar
from atenio.interprete import Interprete
from atenio.modelos import TipoInterpretacion


@pytest.fixture(scope="module")
def interprete():
    return Interprete(cargar_catalogo(), palabras_activacion=("perro",))


def comandos(interpretacion):
    return [paso.comando for orden in interpretacion.ordenes for paso in orden.pasos]


@pytest.mark.parametrize("frase", ["siéntate", "SIÉNTATE", "sientate", "sentarse", "siéntese", "toma asiento", "cientate", "sit"])
def test_sentarse(interprete, frase):
    assert comandos(interprete.interpretar(f"Perro, {frase}")) == ["ksit"]


@pytest.mark.parametrize("frase", ["levántate", "LEVÁNTATE", "arriba", "de pie", "ponte de pie", "en pie", "álzate", "stand up", "levantante"])
def test_levantarse(interprete, frase):
    assert comandos(interprete.interpretar(f"Perro, {frase}")) == ["kup"]


@pytest.mark.parametrize("frase", ["para", "¡Para!", "párate", "quieto", "estate quieto", "alto", "detente", "basta", "no te muevas", "stop"])
def test_parar(interprete, frase):
    assert comandos(interprete.interpretar(f"Perro, {frase}")) == ["krest"]


def test_sin_tildes_igual_que_con_tildes():
    assert normalizar("Siéntate") == normalizar("sientate") == "sientate"


@pytest.mark.parametrize("frase", ["Perro, para sentarte", "siéntate", "Perro, vuela"])
def test_no_activan_ninguna_orden(interprete, frase):
    assert comandos(interprete.interpretar(frase)) == []


def test_descansa_sigue_siendo_tumbarse(interprete):
    assert comandos(interprete.interpretar("Perro, descansa")) == ["d"]
