"""Pruebas de escucha.py sin micrófono ni modelos (T051, base de T057; REQ-17, REQ-18, REQ-24).

`EscuchaFalsa` y `EscuchaMicrofono` con el micrófono falso de test_audio.py y el transcriptor falso.
"""
from __future__ import annotations

import threading
import time

import pytest

from atenio.ajustes import cargar_ajustes
from atenio.escucha import (
    VOZ_POR_DEFECTO,
    ErrorDeVoz,
    EscuchaFalsa,
    EscuchaMicrofono,
    crear_escucha,
    crear_transcriptor,
)
from atenio.interprete import Interprete
from atenio.transcripcion import TranscriptorFalso
from test_audio import microfono_falso, silencio, tono  # noqa: F401 (fixture)


def esperar(condicion, limite_s: float = 2.0) -> None:
    fin = time.monotonic() + limite_s
    while not condicion():
        assert time.monotonic() < fin, "tiempo agotado"
        time.sleep(0.01)


def test_falsa_entrega_las_frases_en_orden_y_se_salta_las_vacias():
    oidas: list[str] = []
    escucha = EscuchaFalsa(["Atenio, siéntate", "", "  ", "Atenio, camina"])
    escucha.iniciar(oidas.append)
    escucha.esperar(2)
    assert oidas == ["Atenio, siéntate", "Atenio, camina"]
    assert escucha.activa is False


def test_falsa_corre_en_su_propio_hilo():
    hilos: list[str] = []
    escucha = EscuchaFalsa(["Atenio, para"])
    escucha.iniciar(lambda _t: hilos.append(threading.current_thread().name))
    escucha.esperar(2)
    assert hilos and hilos[0] != threading.current_thread().name


def test_parar_detiene_el_hilo():
    oidas: list[str] = []
    escucha = EscuchaFalsa(["uno", "dos", "tres"], pausa_s=0.2)
    escucha.iniciar(oidas.append)
    assert escucha.activa is True
    esperar(lambda: oidas == ["uno"])
    escucha.parar()
    assert escucha.activa is False
    time.sleep(0.3)
    assert oidas == ["uno"]


def test_un_fallo_del_receptor_no_para_la_escucha():
    oidas: list[str] = []

    def al_oir(texto):
        if texto == "falla":
            raise ValueError("receptor roto")
        oidas.append(texto)

    escucha = EscuchaFalsa(["falla", "sigue"])
    escucha.iniciar(al_oir)
    escucha.esperar(2)
    assert oidas == ["sigue"]


def test_microfono_falso_calibra_corta_y_transcribe(microfono_falso):
    # 1 s de silencio para calibrar (20 bloques) y luego dos frases separadas por silencio.
    microfono_falso.bloques = [silencio()] * 20 + ([tono()] * 10 + [silencio()] * 20) * 2
    transcriptor = TranscriptorFalso(["Atenio, siéntate", "Atenio, camina"])
    escucha = EscuchaMicrofono(transcriptor, silencio_s=0.5, prerrollo_s=0)
    oidas: list[str] = []
    escucha.iniciar(oidas.append)
    esperar(lambda: len(oidas) == 2)
    escucha.parar()
    assert oidas == ["Atenio, siéntate", "Atenio, camina"]
    assert escucha.umbral is not None
    assert transcriptor.recibido == [20 * 2 * 800, 20 * 2 * 800]  # 10 de voz + 10 de silencio (0,5 s)
    assert escucha.activa is False and escucha.error is None


def test_microfono_texto_vacio_no_llama_al_oir(microfono_falso):
    microfono_falso.bloques = [silencio()] * 20 + [tono()] * 10 + [silencio()] * 20
    transcriptor = TranscriptorFalso([""])
    escucha = EscuchaMicrofono(transcriptor, silencio_s=0.5, prerrollo_s=0)
    oidas: list[str] = []
    escucha.iniciar(oidas.append)
    esperar(lambda: transcriptor.recibido)
    escucha.parar()
    assert oidas == []


def test_microfono_parar_sin_voz_acaba_pronto(microfono_falso):
    microfono_falso.bloques = [silencio()] * 20
    escucha = EscuchaMicrofono(TranscriptorFalso(), silencio_s=0.5)
    escucha.iniciar(lambda _t: None)
    time.sleep(0.2)
    t0 = time.monotonic()
    escucha.parar()
    assert time.monotonic() - t0 < 1.0
    assert escucha.activa is False


def test_microfono_que_no_abre_deja_el_error(monkeypatch):
    import sys
    import types

    modulo = types.ModuleType("sounddevice")

    def falla(**_k):
        raise OSError("sin micrófono")

    modulo.RawInputStream = falla
    monkeypatch.setitem(sys.modules, "sounddevice", modulo)
    escucha = EscuchaMicrofono(TranscriptorFalso())
    escucha.iniciar(lambda _t: None)
    escucha.esperar(2)
    assert escucha.activa is False
    assert isinstance(escucha.error, OSError)


def test_cada_frase_llega_al_interprete(microfono_falso, catalogo, reloj):
    """Lo que hará principal.py: cada `al_oir(texto)` pasa el texto al intérprete."""
    microfono_falso.bloques = [silencio()] * 20 + ([tono()] * 10 + [silencio()] * 20) * 2
    interprete = Interprete(catalogo, reloj=reloj)
    resultados = []
    escucha = EscuchaMicrofono(TranscriptorFalso(["Atenio, siéntate", "Atenio, para"]), silencio_s=0.5, prerrollo_s=0)
    escucha.iniciar(lambda texto: resultados.append(interprete.interpretar(texto)))
    esperar(lambda: len(resultados) == 2)
    escucha.parar()
    assert [r.ordenes[0].id for r in resultados] == ["REQ-02", "REQ-07"]


# --- crear_escucha y ajustes.json ---------------------------------------------------------------


@pytest.mark.pendiente("P-01")
def test_ajustes_json_tiene_la_seccion_voz_provisional():
    a = cargar_ajustes()
    assert "voz" in a.provisionales
    assert a.voz["motor"] in ("vosk", "whisper-tiny", "whisper-base", "falso")
    assert a.voz["silencio_s"] == 0.9 and a.voz["prerrollo_s"] == 0.3  # valores del prototipo I-1
    assert set(a.voz) <= set(VOZ_POR_DEFECTO)


def test_motor_falso_da_escucha_falsa():
    escucha = crear_escucha({"motor": "falso", "frases": ["Atenio, sit"]})
    assert isinstance(escucha, EscuchaFalsa)
    oidas: list[str] = []
    escucha.iniciar(oidas.append)
    escucha.esperar(2)
    assert oidas == ["Atenio, sit"]


def test_acepta_un_objeto_ajustes(tmp_path):
    a = cargar_ajustes()
    falso = type(a)(**{**a.__dict__, "voz": {"motor": "falso"}})
    assert isinstance(crear_escucha(falso), EscuchaFalsa)


def test_motor_desconocido_da_error_claro():
    with pytest.raises(ErrorDeVoz, match="desconocido"):
        crear_transcriptor({**VOZ_POR_DEFECTO, "motor": "siri"})


def test_falta_el_modelo_vosk_dice_donde_va(tmp_path, monkeypatch):
    import atenio.escucha as e

    monkeypatch.setattr(e.importlib.util, "find_spec", lambda _m: object())
    with pytest.raises(ErrorDeVoz, match="alphacephei") as error:
        crear_transcriptor({**VOZ_POR_DEFECTO, "motor": "vosk", "carpeta_modelos": str(tmp_path)})
    assert str(tmp_path) in str(error.value)


def test_falta_el_modelo_whisper_dice_como_bajarlo(tmp_path, monkeypatch):
    import atenio.escucha as e

    monkeypatch.setattr(e.importlib.util, "find_spec", lambda _m: object())
    with pytest.raises(ErrorDeVoz, match="WhisperModel"):
        crear_transcriptor({**VOZ_POR_DEFECTO, "motor": "whisper-tiny", "carpeta_modelos": str(tmp_path)})


def test_falta_la_biblioteca_dice_que_instalar(monkeypatch):
    import atenio.escucha as e

    monkeypatch.setattr(e.importlib.util, "find_spec", lambda _m: None)
    with pytest.raises(ErrorDeVoz, match="requirements-voz.txt"):
        crear_escucha({"motor": "vosk"})
