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


@pytest.mark.parametrize(
    "comando, frases",
    [
        ("kwkF", ["camina", "anda", "avanza", "ve adelante", "hacia delante", "walk", "caminar"]),
        ("kwkL", ["izquierda", "a la izquierda", "turn left"]),
        ("kwkR", ["derecha", "a la derecha", "turn right"]),
        ("d", ["túmbate", "tumbate", "échate", "acuéstate", "al suelo", "lie down", "descansa"]),
        ("khi", ["saluda", "hola", "saludar", "di hola", "hello"]),
        ("kbalance", ["equilíbrate", "equilibrate", "mantén el equilibrio", "balance"]),
        ("ktrF", ["trota", "trotar", "run"]),
    ],
)
def test_resto_de_ordenes_basicas(interprete, comando, frases):
    for frase in frases:
        assert comandos(interprete.interpretar(f"Perro, {frase}")) == [comando], frase


@pytest.mark.parametrize("frase", ["media vuelta", "date media vuelta", "medio giro"])
def test_media_vuelta(interprete, frase):
    assert comandos(interprete.interpretar(f"Perro, {frase}")) == ["kwkL"]


@pytest.mark.parametrize("frase", ["da una vuelta", "date una vuelta", "vuelta completa", "gira sobre ti"])
def test_vuelta_entera(interprete, frase):
    assert comandos(interprete.interpretar(f"Perro, {frase}")) == ["kwkL", "kwkL"]


def test_ninguna_palabra_en_dos_ordenes():
    """El catálogo rechaza una palabra repetida; aquí se comprueba que carga con todo el vocabulario."""
    assert len(cargar_catalogo().palabras_normalizadas()) > 100


def test_ordenes_encadenadas_con_sinonimos(interprete):
    assert comandos(interprete.interpretar("Perro, siéntate y luego saluda")) == ["ksit", "khi"]


def test_sin_tildes_igual_que_con_tildes():
    assert normalizar("Siéntate") == normalizar("sientate") == "sientate"


@pytest.mark.parametrize("frase", ["Perro, para sentarte", "siéntate", "Perro, vuela"])
def test_no_activan_ninguna_orden(interprete, frase):
    assert comandos(interprete.interpretar(frase)) == []


def test_descansa_sigue_siendo_tumbarse(interprete):
    assert comandos(interprete.interpretar("Perro, descansa")) == ["d"]


# Ampliación del 13/11: más formas de decir cada orden (sinónimos, usted/tú, inglés y errores típicos del reconocedor).
AMPLIADAS = [
    (["ksit"], ["siéntate por favor", "ponte sentado", "sit down", "siente", "centate", "sintate", "siéntate aquí"]),
    (["kup"], ["levántate por favor", "levántese", "get up", "stand", "lebantate", "ponte recto", "arriba ya"]),
    (["kwkF"], ["camina hacia adelante", "sigue adelante", "ve para adelante", "echa a andar", "ponte a caminar", "go forward", "avance", "al frente"]),
    (["kwkL"], ["gira izquierda", "ve a izquierda", "tuerce izquierda", "dobla izquierda", "go left", "izquierdo", "por la izquierda"]),
    (["kwkR"], ["gira derecha", "ve a derecha", "tuerce derecha", "dobla derecha", "go right", "derecho", "por la derecha"]),
    (["krest"], ["para ya", "frena", "quédate quieto", "deja de moverte", "alto ahí", "freeze", "stay", "parar"]),
    (["d"], ["échate al suelo", "ponte tumbado", "a descansar", "relájate", "lay down", "tumbado", "acostado"]),
    (["khi"], ["saluda a todos", "dile hola", "say hi", "wave", "buenas", "buenos días", "saludos", "hey"]),
    (["kbalance"], ["equilíbrate por favor", "mantente en equilibrio", "balancea", "keep balance", "haz equilibrio", "no te caigas"]),
    (["ktrF"], ["trota rápido", "trota un poco", "jog", "a trotar", "trotecito", "al trote"]),
    (["kwkL"], ["haz media vuelta", "dar media vuelta", "date la vuelta", "turn around", "gírate", "media buelta"]),
    (["kwkL", "kwkL"], ["dar una vuelta", "gira en redondo", "una vuelta", "giro completo", "spin around", "full turn", "vuelta entera"]),
]


@pytest.mark.parametrize("esperado, frases", AMPLIADAS, ids=lambda v: "+".join(v) if v and isinstance(v[0], str) and len(v[0]) < 9 and " " not in v[0] else "frases")
def test_vocabulario_ampliado(interprete, esperado, frases):
    for frase in frases:
        assert comandos(interprete.interpretar(f"Perro, {frase}")) == esperado, frase


def test_baila_sigue_sin_secuencia(interprete):
    """REQ-14 no tiene pasos (OPEN-08): sus nuevas formas deben dar «orden no disponible», no otra orden."""
    for frase in ["baila ya", "danza", "mueve el esqueleto", "let's dance"]:
        resultado = interprete.interpretar(f"Perro, {frase}")
        assert resultado.tipo == TipoInterpretacion.FUERA_DEL_CATALOGO, frase
        assert comandos(resultado) == [], frase


@pytest.mark.parametrize("frase", ["para sentarse", "para caminar", "ve", "gira", "da una", "una", "vuelta"])
def test_frases_parciales_no_chocan_con_otra_orden(interprete, frase):
    """Una frase incompleta o ambigua no debe activar ninguna orden (coincidencia exacta de la frase entera)."""
    assert comandos(interprete.interpretar(f"Perro, {frase}")) == [], frase


def test_nuevas_formas_encadenadas(interprete):
    assert comandos(interprete.interpretar("Perro, ponte sentado y luego trota rápido")) == ["ksit", "ktrF"]
    assert comandos(interprete.interpretar("Perro, buenas y luego échate al suelo")) == ["khi", "d"]
    assert comandos(interprete.interpretar("Perro, ve izquierda y luego frena y luego saluda")) == ["kwkL", "krest"]
