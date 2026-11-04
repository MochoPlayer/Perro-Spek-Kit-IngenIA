"""Eventos hacia la interfaz (plan.md, «Modelo de datos»: tipo y texto). Cubre REQ-19 (parte de eventos).

Una lista y suscriptores simples, sin interfaz real: las pruebas leen la lista (D-07, D-09).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class TipoEvento(Enum):
    """Los cuatro tipos de plan.md: texto reconocido, orden interpretada, estado de conexión, aviso."""

    TEXTO_RECONOCIDO = "texto_reconocido"
    ORDEN_INTERPRETADA = "orden_interpretada"
    ESTADO_CONEXION = "estado_conexion"
    AVISO = "aviso"


# Textos de aviso. Los dos primeros son exactos de spec.md (REQ-25, REQ-30).
AVISO_NO_CONECTADO = "robot no conectado"  # REQ-25
AVISO_PARADA_ACTIVA = "parada de emergencia activa"  # REQ-30
AVISO_BATERIA_BAJA = "batería baja: hay que cargar el robot"  # REQ-33 (spec.md no fija el texto exacto)
AVISO_CONEXION_PERDIDA = "se ha perdido la conexión con el robot: cola vaciada"  # D-13, P-08 (texto provisional)


@dataclass(frozen=True)
class Evento:
    tipo: TipoEvento
    texto: str


class Eventos:
    """Guarda cada evento en `lista` y lo pasa a los suscriptores, en orden de llegada."""

    def __init__(self) -> None:
        self.lista: list[Evento] = []
        self._suscriptores: list[Callable[[Evento], None]] = []

    def suscribir(self, funcion: Callable[[Evento], None]) -> None:
        self._suscriptores.append(funcion)

    def publicar(self, tipo: TipoEvento, texto: str) -> None:
        evento = Evento(tipo, texto)
        self.lista.append(evento)
        for funcion in self._suscriptores:
            funcion(evento)

    # --- consultas para las pruebas ---
    def textos(self, tipo: TipoEvento) -> list[str]:
        return [e.texto for e in self.lista if e.tipo is tipo]

    @property
    def avisos(self) -> list[str]:
        return self.textos(TipoEvento.AVISO)
