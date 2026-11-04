"""Interfaz de ordenador: página web local (D-07; P-06 sigue pendiente del equipo). Cubre T056, REQ-19, REQ-30."""
from .servidor import HOST, crear_servidor, servir_en_hilo

__all__ = ["HOST", "crear_servidor", "servir_en_hilo"]
