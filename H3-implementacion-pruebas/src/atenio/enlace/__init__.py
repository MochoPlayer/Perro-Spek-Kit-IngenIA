# Enlace con el robot: interfaz única, versión simulada y versión serie (D-03).
from .base import Enlace, es_bateria_baja
from .serie import EnlaceSerie
from .simulado import EnlaceSimulado

__all__ = ["Enlace", "EnlaceSerie", "EnlaceSimulado", "es_bateria_baja"]
