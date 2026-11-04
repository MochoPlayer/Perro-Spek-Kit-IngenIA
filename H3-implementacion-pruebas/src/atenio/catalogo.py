"""Carga y consulta del catálogo de órdenes (datos/catalogo.json, decisión D-05).

Cubre REQ-02 a REQ-11 (Nivel 1) y REQ-14 a REQ-16 (Nivel 2, opcionales).
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from atenio.modelos import Orden, Paso

RUTA_POR_DEFECTO = Path(__file__).resolve().parents[2] / "datos" / "catalogo.json"


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin signos de puntuación y con un solo espacio (H1 §2.4).

    La «ñ» se conserva: no es una tilde y cambia la palabra.
    """
    texto = texto.lower().replace("ñ", "\0")
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace("\0", "ñ")
    texto = "".join(c if c.isalnum() else " " for c in texto)
    return " ".join(texto.split())


class ErrorCatalogo(ValueError):
    """El fichero del catálogo no tiene el formato esperado."""


class Catalogo:
    """Órdenes del catálogo, con búsqueda por palabra normalizada."""

    def __init__(self, ordenes: list[Orden]):
        self._ordenes = tuple(ordenes)
        self._por_palabra: dict[str, Orden] = {}
        ids: set[str] = set()
        for orden in self._ordenes:
            if orden.id in ids:
                raise ErrorCatalogo(f"id repetido en el catálogo: {orden.id}")
            ids.add(orden.id)
            if not orden.palabras:
                raise ErrorCatalogo(f"{orden.id} no tiene ninguna palabra")
            for palabra in orden.palabras:
                clave = normalizar(palabra)
                if not clave:
                    raise ErrorCatalogo(f"{orden.id} tiene una palabra vacía")
                if clave in self._por_palabra and self._por_palabra[clave] is not orden:
                    otra = self._por_palabra[clave].id
                    raise ErrorCatalogo(f"«{palabra}» está en {otra} y en {orden.id}")
                self._por_palabra[clave] = orden

    @property
    def ordenes(self) -> tuple[Orden, ...]:
        return self._ordenes

    def __len__(self) -> int:
        return len(self._ordenes)

    def por_id(self, id_orden: str) -> Orden:
        for orden in self._ordenes:
            if orden.id == id_orden:
                return orden
        raise KeyError(id_orden)

    def buscar(self, texto: str) -> Orden | None:
        """Devuelve la orden cuya palabra coincide con el texto normalizado, o None."""
        return self._por_palabra.get(normalizar(texto))

    def palabras_normalizadas(self) -> tuple[str, ...]:
        return tuple(self._por_palabra)

    def max_palabras_por_orden(self) -> int:
        """Número de palabras de la expresión más larga del catálogo (p. ej. «da una vuelta» = 3)."""
        return max(len(p.split()) for p in self._por_palabra)


def _paso_desde_dict(datos: dict, id_orden: str) -> Paso:
    try:
        comando = datos["comando"]
    except KeyError as exc:
        raise ErrorCatalogo(f"{id_orden}: un paso no tiene «comando»") from exc
    if not isinstance(comando, str) or not comando:
        raise ErrorCatalogo(f"{id_orden}: comando vacío o no es texto")
    duracion = datos.get("duracion_s")
    if duracion is not None:
        duracion = float(duracion)
        if duracion < 0:
            raise ErrorCatalogo(f"{id_orden}: duración negativa en {comando}")
    return Paso(comando=comando, duracion_s=duracion)


def cargar_catalogo(ruta: str | Path | None = None) -> Catalogo:
    """Lee el catálogo de un fichero JSON (por defecto, datos/catalogo.json)."""
    ruta = Path(ruta) if ruta is not None else RUTA_POR_DEFECTO
    with open(ruta, encoding="utf-8") as fichero:
        datos = json.load(fichero)
    if "ordenes" not in datos or not isinstance(datos["ordenes"], list):
        raise ErrorCatalogo("falta la lista «ordenes»")
    ordenes = []
    for entrada in datos["ordenes"]:
        id_orden = entrada.get("id")
        if not id_orden:
            raise ErrorCatalogo("una orden no tiene «id»")
        pasos = tuple(_paso_desde_dict(p, id_orden) for p in entrada.get("pasos", []))
        ordenes.append(
            Orden(
                id=id_orden,
                palabras=tuple(entrada.get("palabras", [])),
                pasos=pasos,
                interrumpe=bool(entrada.get("interrumpe", False)),
            )
        )
    return Catalogo(ordenes)
