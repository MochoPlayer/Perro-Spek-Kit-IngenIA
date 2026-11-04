"""Modelo de datos compartido: Paso, Orden, TipoInterpretacion e Interpretacion.

Contrato común entre intérprete y gestor de acciones (plan.md, «Modelo de datos»). No cambiar sin acordarlo.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Paso:
    """Un comando del protocolo serie de Petoi y su duración estimada (None = por medir, D-06)."""

    comando: str
    duracion_s: float | None


@dataclass(frozen=True)
class Orden:
    """Orden del catálogo. `id` es el REQ-NN que la define (por ejemplo «REQ-02»)."""

    id: str
    palabras: tuple[str, ...]
    pasos: tuple[Paso, ...]
    interrumpe: bool = False


class TipoInterpretacion(Enum):
    """Clases de resultado del intérprete (plan.md, «Modelo de datos»)."""

    ORDENES = "ordenes"
    NO_ENTENDIDA = "no_entendida"
    FUERA_DEL_CATALOGO = "fuera_del_catalogo"
    SOLO_ACTIVACION = "solo_activacion"
    IGNORADA = "ignorada"


@dataclass(frozen=True)
class Interpretacion:
    """Salida del intérprete: tipo, órdenes en el orden dicho y avisos para la pantalla."""

    tipo: TipoInterpretacion
    ordenes: tuple[Orden, ...] = ()
    avisos: tuple[str, ...] = ()
