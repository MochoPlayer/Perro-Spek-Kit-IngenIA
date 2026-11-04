"""Pruebas de audio.py sin micrófono: detector de frase con bloques sintéticos y micrófono falso (REQ-17, REQ-24).

Los bloques de «voz» son un tono; los de silencio, ceros. `sounddevice` se sustituye por un módulo falso.
"""
from __future__ import annotations

import math
import sys
import types
from array import array

import pytest

from atenio.audio import (
    BLOQUE_S,
    MUESTRAS_POR_BLOQUE,
    UMBRAL_MINIMO,
    CapturaMicrofono,
    DetectorDeFrase,
    MedidorNivel,
    calibrar_umbral,
    rms,
)


def tono(amplitud: int = 5000) -> bytes:
    return array("h", (int(amplitud * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(MUESTRAS_POR_BLOQUE))).tobytes()


def silencio() -> bytes:
    return bytes(2 * MUESTRAS_POR_BLOQUE)


def con_horas(bloques: list[bytes]) -> list[tuple[bytes, float]]:
    return [(b, i * BLOQUE_S) for i, b in enumerate(bloques)]


def test_rms_de_silencio_y_de_tono():
    assert rms(silencio()) == 0.0
    assert rms(tono(5000)) == pytest.approx(5000 / math.sqrt(2), rel=0.02)
    assert rms(b"") == 0.0


def test_frase_empieza_con_la_voz_y_acaba_tras_el_silencio():
    bloques = [silencio()] * 10 + [tono()] * 20 + [silencio()] * 30
    detector = DetectorDeFrase(silencio_fin_s=0.5, prerrollo_s=0.1)
    frase = detector.cortar(con_horas(bloques))
    assert frase is not None
    # 2 de prerrollo + 20 de voz + 10 de silencio (0,5 s / 50 ms)
    assert len(frase.audio) == (2 + 20 + 10) * 2 * MUESTRAS_POR_BLOQUE
    assert frase.fin_voz == pytest.approx(29 * BLOQUE_S)
    assert frase.cierre - frase.fin_voz == pytest.approx(0.5)


def test_sin_voz_no_hay_frase():
    detector = DetectorDeFrase(espera_voz_s=1.0)
    assert detector.cortar(con_horas([silencio()] * 100)) is None


def test_frase_larga_se_corta_en_el_maximo():
    detector = DetectorDeFrase(max_frase_s=1.0, prerrollo_s=0)
    frase = detector.cortar(con_horas([tono()] * 100))
    assert frase is not None
    assert frase.duracion_s == pytest.approx(1.0)


def test_pausa_corta_no_parte_la_frase():
    bloques = [tono()] * 10 + [silencio()] * 4 + [tono()] * 10 + [silencio()] * 20
    frase = DetectorDeFrase(silencio_fin_s=0.5, prerrollo_s=0).cortar(con_horas(bloques))
    assert frase is not None
    assert frase.fin_voz == pytest.approx(23 * BLOQUE_S)


def test_valores_por_defecto_esperan_0_9_s_y_guardan_0_3_s_antes():
    bloques = [silencio()] * 20 + [tono()] * 10 + [silencio()] * 40
    frase = DetectorDeFrase().cortar(con_horas(bloques))
    assert frase is not None
    assert frase.cierre - frase.fin_voz == pytest.approx(0.9)
    # 6 bloques de prerrollo (0,3 s) + 10 de voz + 18 de silencio (0,9 s)
    assert len(frase.audio) == (6 + 10 + 18) * 2 * MUESTRAS_POR_BLOQUE
    assert frase.voz_s == pytest.approx(0.5)
    assert frase.duracion_s == pytest.approx(0.3 + 0.5 + 0.9)


def test_final_flojo_sigue_siendo_voz():
    """Una sílaba final más baja que el umbral de inicio (pero sobre umbral × 0,6) no corta la frase."""
    umbral = 3000
    bloques = [tono(6000)] * 10 + [tono(3000)] * 6 + [silencio()] * 30  # RMS ≈ 4243 y ≈ 2121
    frase = DetectorDeFrase(umbral, prerrollo_s=0).cortar(con_horas(bloques))
    assert frase is not None
    assert frase.fin_voz == pytest.approx(15 * BLOQUE_S)
    assert frase.voz_s == pytest.approx(16 * BLOQUE_S)


def test_calibrar_umbral_no_baja_del_minimo():
    assert calibrar_umbral([silencio()] * 5) == UMBRAL_MINIMO
    assert calibrar_umbral([tono(1000)] * 5, factor=3.0) == pytest.approx(3 * 1000 / math.sqrt(2), rel=0.02)


class _FlujoFalso:
    """Sustituye a sounddevice.RawInputStream: al arrancar, entrega los bloques al callback."""

    bloques: list[bytes] = []

    def __init__(self, *, samplerate, blocksize, channels, dtype, device, callback):
        assert (samplerate, blocksize, channels, dtype) == (16000, MUESTRAS_POR_BLOQUE, 1, "int16")
        self._callback = callback
        self.cerrado = False

    def start(self):
        for b in self.bloques:
            self._callback(b, MUESTRAS_POR_BLOQUE, None, None)

    def stop(self):
        pass

    def close(self):
        self.cerrado = True


@pytest.fixture
def microfono_falso(monkeypatch):
    modulo = types.ModuleType("sounddevice")
    modulo.RawInputStream = _FlujoFalso
    monkeypatch.setitem(sys.modules, "sounddevice", modulo)
    return _FlujoFalso


def test_captura_con_microfono_falso(microfono_falso):
    microfono_falso.bloques = [tono()] * 10 + [silencio()] * 20
    horas = iter(i * BLOQUE_S for i in range(1000))
    captura = CapturaMicrofono(reloj=lambda: next(horas))
    captura.abrir()
    try:
        bloques = captura.bloques()
        frase = DetectorDeFrase(silencio_fin_s=0.5, prerrollo_s=0).cortar(next(bloques) for _ in range(30))
    finally:
        captura.cerrar()
    assert frase is not None
    assert len(frase.audio) == 20 * 2 * MUESTRAS_POR_BLOQUE
    assert isinstance(frase.audio, bytes)


# --- nivel del micrófono para la onda de la interfaz (solo números, REQ-24) -----------------------


def test_medidor_devuelve_solo_lo_nuevo_y_guarda_un_maximo():
    m = MedidorNivel(maximo=3)
    assert m.desde(0) == ([], 0)
    for v in (10, 20, 30, 40):
        m.anotar(v)
    assert m.desde(0) == ([20.0, 30.0, 40.0], 4)  # solo quedan los 3 últimos
    assert m.desde(3) == ([40.0], 4)
    assert m.desde(4) == ([], 4)
    assert m.desde(99) == ([], 4)
    assert all(isinstance(v, float) for v in m.desde(0)[0])


def test_la_captura_anota_el_nivel_de_cada_bloque(microfono_falso):
    microfono_falso.bloques = [silencio()] * 3 + [tono(1000)] * 2
    medidor = MedidorNivel()
    captura = CapturaMicrofono(medidor=medidor)
    captura.abrir()
    captura.cerrar()
    valores, total = medidor.desde(0)
    assert total == 5
    assert valores[:3] == [0.0, 0.0, 0.0]
    assert valores[3] == pytest.approx(1000 / math.sqrt(2), rel=0.02)
