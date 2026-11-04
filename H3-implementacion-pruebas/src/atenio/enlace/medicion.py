"""Medición de comandos con el robot real para la sesión 2 (T069, T070, T071, T080).

Envía un comando por el enlace, cronometra hasta que la persona que observa marca el fin y guarda
lo que devuelve el robot. La lógica no depende del teclado ni del puerto: las pruebas la usan con
`EnlaceSimulado` y `RelojSimulado` (REQ-26). La consola está en `herramientas/sesion_robot.py`.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from atenio.enlace.base import Enlace, cadena_prohibida
from atenio.reloj import Reloj


@dataclass
class Medida:
    comando: str
    inicio: float
    duracion_s: float | None = None  # None: el comando no terminó solo (marcha continua) o no se marcó
    respuestas: list[str] = field(default_factory=list)
    nota: str = ""


class ErrorMedicion(RuntimeError):
    """No se puede medir: sin conexión, comando prohibido o sin medida en curso."""


class SesionMedida:
    def __init__(self, enlace: Enlace, reloj: Reloj) -> None:
        self._enlace = enlace
        self._reloj = reloj
        self.medidas: list[Medida] = []
        self._en_curso: Medida | None = None

    @property
    def en_curso(self) -> Medida | None:
        return self._en_curso

    def enviar(self, comando: str) -> Medida:
        """Envía el comando y empieza a cronometrar. Cierra antes la medida anterior sin duración."""
        comando = comando.strip()
        if not comando:
            raise ErrorMedicion("comando vacío")
        if cadena_prohibida(comando):  # REQ-34, D-12: nunca G ni g
            raise ErrorMedicion(f"«{comando}» está prohibido (giroscopio, D-12)")
        if not self._enlace.conectado:
            raise ErrorMedicion("robot no conectado")
        if self._en_curso is not None:
            self.terminar(None, nota="interrumpido por el siguiente comando")
        inicio = self._reloj.ahora()
        if not self._enlace.enviar(comando):
            raise ErrorMedicion(f"no se pudo enviar «{comando}»: se ha perdido la conexión")
        self._en_curso = Medida(comando, inicio)
        return self._en_curso

    def leer(self) -> list[str]:
        """Recoge las líneas que ha enviado el robot y las guarda en la medida en curso."""
        lineas = self._enlace.leer_lineas()
        if self._en_curso is not None:
            self._en_curso.respuestas.extend(lineas)
        return lineas

    def terminar(self, fin: float | None = -1.0, nota: str = "") -> Medida:
        """Cierra la medida en curso. Por defecto, la duración es hasta ahora; `None` = no terminó sola."""
        if self._en_curso is None:
            raise ErrorMedicion("no hay ningún comando en curso")
        self.leer()
        medida = self._en_curso
        if fin is None:
            medida.duracion_s = None
        else:
            hora_fin = self._reloj.ahora() if fin < 0 else fin
            medida.duracion_s = round(hora_fin - medida.inicio, 2)
        medida.nota = nota
        self.medidas.append(medida)
        self._en_curso = None
        return medida

    def guardar_csv(self, ruta: str | Path) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", newline="", encoding="utf-8") as fichero:
            escritor = csv.writer(fichero)
            escritor.writerow(["comando", "duracion_s", "respuestas", "nota"])
            for m in self.medidas:
                duracion = "" if m.duracion_s is None else f"{m.duracion_s:.2f}"
                escritor.writerow([m.comando, duracion, " | ".join(m.respuestas), m.nota])
        return ruta


def interpretar_fin_de_linea(texto: str) -> str:
    """Convierte «\\n», «\\r\\n» o «ninguno» (lo que se escribe en la consola) en el texto real."""
    if texto.lower() in ("ninguno", "none", ""):
        return ""
    return texto.replace("\\r", "\r").replace("\\n", "\n")
