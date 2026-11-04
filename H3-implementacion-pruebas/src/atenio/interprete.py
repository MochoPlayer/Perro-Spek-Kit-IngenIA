"""Intérprete (componente 3 de plan.md): texto reconocido → Interpretacion.

Cubre REQ-01, REQ-02 a REQ-16 (búsqueda en el catálogo), REQ-12, REQ-13, REQ-18, REQ-23, REQ-29 y REQ-35.
"""
from __future__ import annotations

from typing import Protocol

from atenio.catalogo import Catalogo, normalizar
from atenio.modelos import Interpretacion, Orden, TipoInterpretacion

AVISO_NO_ENTENDIDA = "no se ha entendido bien"  # REQ-12 (texto exacto de spec.md)
AVISO_NO_DISPONIBLE = "orden no disponible"  # REQ-13 (spec.md no fija el texto exacto)

PALABRAS_ACTIVACION = ("atenio",)  # OPEN-01: el repo no da variantes de transcripción
PALABRAS_ENLACE = ("y", "luego")  # valor inicial de spec.md, casos límite (P-03)
ESPERA_ACTIVACION_S = 5.0  # REQ-35, provisional (OPEN-02)


class FuenteDeHora(Protocol):
    """Cualquier objeto con `.ahora()` en segundos (el reloj real o el simulado, D-08)."""

    def ahora(self) -> float: ...


def aviso_no_disponible(parte: str) -> str:
    return f"{AVISO_NO_DISPONIBLE}: «{parte}»"


class Interprete:
    """Convierte una frase de texto en una Interpretacion.

    Su único estado es la espera de REQ-35: tras «Atenio» solo, la siguiente frase dentro de
    `espera_s` segundos cuenta como orden aunque no empiece por «Atenio».
    """

    def __init__(
        self,
        catalogo: Catalogo,
        *,
        reloj: FuenteDeHora | None = None,
        espera_s: float = ESPERA_ACTIVACION_S,
        palabras_activacion: tuple[str, ...] = PALABRAS_ACTIVACION,
        palabras_enlace: tuple[str, ...] = PALABRAS_ENLACE,
        max_ordenes: int | None = None,
        max_palabras_orden: int | None = None,
        para_descarta_resto: bool = True,
    ):
        """Parámetros (todos provisionales; los valores finales irán en ajustes.json):

        - `max_ordenes`: máximo de órdenes por frase; None = sin límite (por decidir, P-03).
        - `max_palabras_orden`: una parte no reconocida con más palabras que esto, o con
          cifras, se clasifica como «no entendida» y no como «fuera del catálogo». Por defecto,
          la expresión más larga del catálogo. Regla provisional mientras no se resuelva Y-02.
        - `para_descarta_resto`: una orden que interrumpe («para») descarta lo que queda de la
          frase (D-10, opción A; P-04 / OPEN-12).
        """
        self._catalogo = catalogo
        self._reloj = reloj
        self._espera_s = espera_s
        self._activacion = tuple(normalizar(p) for p in palabras_activacion)
        self._enlace = frozenset(normalizar(p) for p in palabras_enlace)
        if max_ordenes is not None and max_ordenes < 1:
            raise ValueError("max_ordenes debe ser al menos 1")
        self._max_ordenes = max_ordenes
        self._max_palabras = (
            max_palabras_orden if max_palabras_orden is not None else catalogo.max_palabras_por_orden()
        )
        self._para_descarta_resto = para_descarta_resto
        self._activado_en: float | None = None
        for palabra in catalogo.palabras_normalizadas():
            if self._enlace.intersection(palabra.split()):
                raise ValueError(f"la palabra del catálogo «{palabra}» contiene una palabra de enlace")

    # ------------------------------------------------------------------ estado de REQ-35

    @property
    def esperando_orden(self) -> bool:
        """True si hay una activación pendiente (puede haber caducado; se mira al interpretar)."""
        return self._activado_en is not None

    def _hora(self, ahora: float | None) -> float | None:
        if ahora is not None:
            return ahora
        if self._reloj is not None:
            return self._reloj.ahora()
        return None

    def _activacion_vigente(self, ahora: float | None) -> bool:
        if self._activado_en is None:
            return False
        if ahora is None:
            raise ValueError("hace falta la hora (parámetro `ahora` o un reloj) para la espera de REQ-35")
        return ahora - self._activado_en <= self._espera_s

    # ------------------------------------------------------------------ interpretación

    def interpretar(self, texto: str, ahora: float | None = None) -> Interpretacion:
        """Interpreta una frase. `ahora` (segundos) manda sobre el reloj inyectado."""
        hora = self._hora(ahora)
        palabras = normalizar(texto).split()

        if palabras and palabras[0] in self._activacion:
            resto = palabras[1:]
            if not resto:
                if hora is None:
                    raise ValueError("hace falta la hora (parámetro `ahora` o un reloj) para la espera de REQ-35")
                self._activado_en = hora  # REQ-35: abre (o reabre) la espera
                return Interpretacion(TipoInterpretacion.SOLO_ACTIVACION)
            self._activado_en = None
            return self._interpretar_ordenes(resto)

        if self._activacion_vigente(hora):  # REQ-35: frase sin «Atenio» dentro de la espera
            self._activado_en = None
            if not palabras:
                return Interpretacion(TipoInterpretacion.NO_ENTENDIDA, avisos=(AVISO_NO_ENTENDIDA,))
            return self._interpretar_ordenes(palabras)

        self._activado_en = None
        return Interpretacion(TipoInterpretacion.IGNORADA)  # REQ-01

    def _partir(self, palabras: list[str]) -> list[str]:
        """Parte la frase por las palabras de enlace (REQ-29). Las partes vacías se descartan."""
        partes: list[str] = []
        actual: list[str] = []
        for palabra in palabras:
            if palabra in self._enlace:
                if actual:
                    partes.append(" ".join(actual))
                actual = []
            else:
                actual.append(palabra)
        if actual:
            partes.append(" ".join(actual))
        return partes

    def _parece_orden(self, parte: str) -> bool:
        """Regla provisional (Y-02): sin cifras y con pocas palabras → orden fuera del catálogo."""
        palabras = parte.split()
        return len(palabras) <= self._max_palabras and all(p.isalpha() for p in palabras)

    def _interpretar_ordenes(self, palabras: list[str]) -> Interpretacion:
        partes = self._partir(palabras)
        if not partes:  # p. ej. «Atenio y luego»
            return Interpretacion(TipoInterpretacion.NO_ENTENDIDA, avisos=(AVISO_NO_ENTENDIDA,))

        ordenes: list[Orden] = []
        avisos: list[str] = []
        hay_no_entendida = False
        for indice, parte in enumerate(partes):
            orden = self._catalogo.buscar(parte)
            if orden is None:
                if self._parece_orden(parte):
                    avisos.append(aviso_no_disponible(parte))
                else:
                    hay_no_entendida = True
                    if AVISO_NO_ENTENDIDA not in avisos:
                        avisos.append(AVISO_NO_ENTENDIDA)
                continue
            if not orden.pasos:  # orden en el catálogo pero sin comandos definidos (REQ-14, OPEN-08)
                avisos.append(aviso_no_disponible(parte))
                continue
            if self._max_ordenes is not None and len(ordenes) >= self._max_ordenes:
                avisos.append(f"máximo de {self._max_ordenes} órdenes por frase: se descarta «{parte}»")
                continue
            ordenes.append(orden)
            if orden.interrumpe and self._para_descarta_resto:
                descartadas = partes[indice + 1 :]
                if descartadas:
                    lista = ", ".join(f"«{p}»" for p in descartadas)
                    avisos.append(f"«{parte}» descarta el resto de la frase: {lista}")
                break

        if ordenes:
            return Interpretacion(TipoInterpretacion.ORDENES, tuple(ordenes), tuple(avisos))
        tipo = TipoInterpretacion.NO_ENTENDIDA if hay_no_entendida else TipoInterpretacion.FUERA_DEL_CATALOGO
        return Interpretacion(tipo, (), tuple(avisos))
