"""Arranque del sistema (componente 1 de plan.md): catálogo → intérprete → gestor → enlace → eventos.

Cubre T019, T045 y parte de T057 (REQ-19, REQ-26, REQ-27). La voz es opcional: `escucha` sigue el contrato de
`atenio.escucha` (iniciar(al_oir), parar(), activa) por tipado de pato. Sin voz, las frases llegan por `oir()`.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable

from atenio.ajustes import RUTA_POR_DEFECTO as RUTA_AJUSTES
from atenio.ajustes import Ajustes, cargar_ajustes
from atenio.catalogo import Catalogo, cargar_catalogo
from atenio.enlace.base import Enlace
from atenio.enlace.serie import EnlaceSerie
from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import Evento, Eventos, TipoEvento
from atenio.gestor_acciones import GestorAcciones
from atenio.interprete import Interprete
from atenio.reloj import Reloj, RelojReal

TIPOS_ENLACE = ("simulado", "serie")
PERIODO_TICK_S = 0.05  # cada cuánto avanza el gestor con el reloj real (valor de diseño, no medido)


def tipo_enlace_de_ajustes(ruta: str | Path | None = None) -> str:
    """T045: lee la clave «enlace» de ajustes.json («simulado» si no está)."""
    datos = json.loads(Path(ruta or RUTA_AJUSTES).read_text(encoding="utf-8"))
    tipo = datos.get("enlace", {}).get("valor", "simulado")
    if tipo not in TIPOS_ENLACE:
        raise ValueError(f"enlace desconocido en ajustes.json: «{tipo}» (valores: {', '.join(TIPOS_ENLACE)})")
    return tipo


def crear_enlace(tipo: str, ajustes: Ajustes, reloj: Reloj) -> Enlace:
    """T045, D-03: el mismo programa con el robot simulado o con el puerto serie real."""
    if tipo == "simulado":
        return EnlaceSimulado(reloj)
    if tipo == "serie":
        return EnlaceSerie(ajustes.puerto, ajustes.baudios, ajustes.fin_de_linea)
    raise ValueError(f"enlace desconocido: «{tipo}»")


class EnlaceConRegistro:
    """Envuelve cualquier enlace y anota cada cadena enviada con éxito, para mostrarla en la interfaz."""

    def __init__(self, enlace: Enlace, reloj: Reloj) -> None:
        self.interno = enlace
        self._reloj = reloj
        self.registro: list[tuple[float, str]] = []

    @property
    def conectado(self) -> bool:
        return self.interno.conectado

    def conectar(self) -> bool:
        return self.interno.conectar()

    def desconectar(self) -> None:
        self.interno.desconectar()

    def enviar(self, cadena: str) -> bool:
        ok = self.interno.enviar(cadena)
        if ok:
            self.registro.append((self._reloj.ahora(), cadena))
        return ok

    def leer_lineas(self) -> list[str]:
        return self.interno.leer_lineas()


class Sistema:
    """Monta los componentes y los protege con un cerrojo: la interfaz, la voz y el bucle usan hilos distintos."""

    def __init__(
        self,
        enlace: Enlace,
        reloj: Reloj,
        *,
        catalogo: Catalogo | None = None,
        ajustes: Ajustes | None = None,
        escucha=None,
        inactividad_s: float | None = None,
        duracion_desconocida_s: float | None = None,
    ) -> None:
        self.reloj = reloj
        self._inicio = reloj.ahora()  # el registro de la interfaz cuenta desde el arranque
        self.ajustes = ajustes if ajustes is not None else cargar_ajustes()
        self.catalogo = catalogo if catalogo is not None else cargar_catalogo()
        self.enlace = EnlaceConRegistro(enlace, reloj)
        self.eventos = Eventos()
        self._horas: list[str] = []  # hora de pared de cada evento, para la pantalla
        self.eventos.suscribir(lambda _e: self._horas.append(time.strftime("%H:%M:%S")))
        self.interprete = Interprete(
            self.catalogo,
            reloj=reloj,
            espera_s=self.ajustes.espera_orden_s,
            max_ordenes=self.ajustes.max_ordenes_por_frase,
        )
        self.gestor = GestorAcciones(
            self.enlace,
            reloj,
            self.eventos,
            self.ajustes,
            inactividad_s=inactividad_s,
            duracion_desconocida_s=duracion_desconocida_s,
        )
        self.escucha = escucha
        self.cerrojo = threading.RLock()
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None

    # ------------------------------------------------------------------ entradas

    def oir(self, texto: str) -> None:
        """Una frase (de la voz o de la caja de texto): evento «texto reconocido» y al intérprete."""
        texto = texto.strip()
        if not texto:
            return
        with self.cerrojo:
            self.eventos.publicar(TipoEvento.TEXTO_RECONOCIDO, texto)
            self.gestor.recibir(self.interprete.interpretar(texto))

    def pulsar_parada(self) -> None:
        """Botón de parada de emergencia (REQ-30)."""
        with self.cerrojo:
            self.gestor.pulsar_parada()

    def tick(self) -> None:
        with self.cerrojo:
            self.gestor.tick()

    # ------------------------------------------------------------------ ciclo de vida

    def arrancar(self, *, con_bucle: bool = True) -> None:
        """Conecta el enlace (publica el estado, T060), arranca la voz si hay y el bucle de tick()."""
        with self.cerrojo:
            self.gestor.conectar()
        if self.escucha is not None:
            self.escucha.iniciar(self.oir)
        if con_bucle:
            self._parar.clear()
            self._hilo = threading.Thread(target=self._bucle, name="atenio-tick", daemon=True)
            self._hilo.start()

    def detener(self) -> None:
        if self.escucha is not None:
            self.escucha.parar()
        self._parar.set()
        if self._hilo is not None:
            self._hilo.join(timeout=1)
            self._hilo = None
        with self.cerrojo:
            self.enlace.desconectar()

    def _bucle(self) -> None:
        while not self._parar.wait(PERIODO_TICK_S):
            self.tick()

    # ------------------------------------------------------------------ consultas para la interfaz

    @property
    def voz_activa(self) -> bool:
        return bool(self.escucha is not None and getattr(self.escucha, "activa", False))

    def foto(self, desde: int = 0) -> dict:
        """Estado actual y eventos a partir del número `desde` (para la interfaz)."""
        with self.cerrojo:
            eventos = self.eventos.lista[desde:]
            return {
                "estado": self.gestor.estado.value,
                "conectado": self.enlace.conectado,
                "parada": self.gestor.estado.value == "Parada",
                "voz_activa": self.voz_activa,
                "cola": len(self.gestor.cola),
                "desde": desde,
                "total_eventos": desde + len(eventos),
                "eventos": [{"tipo": e.tipo.value, "texto": self._para_pantalla(e), "hora": h}
                            for e, h in zip(eventos, self._horas[desde:])],
                "registro": [{"t": round(t - self._inicio, 2), "comando": c} for t, c in self.enlace.registro[-50:]],
            }

    def _para_pantalla(self, e: Evento) -> str:
        """La orden interpretada se publica con su REQ («REQ-04»); en pantalla va también su palabra."""
        if e.tipo is TipoEvento.ORDEN_INTERPRETADA:
            try:
                return f"{self.catalogo.por_id(e.texto).palabras[0]} ({e.texto})"
            except (KeyError, IndexError, ValueError):
                return e.texto
        return e.texto

    def suscribir(self, funcion: Callable[[Evento], None]) -> None:
        self.eventos.suscribir(funcion)


def crear_sistema(tipo_enlace: str | None = None, *, escucha=None, reloj: Reloj | None = None) -> Sistema:
    """Monta el sistema con el reloj real y el enlace de ajustes.json (o el que se pida)."""
    reloj = reloj if reloj is not None else RelojReal()
    ajustes = cargar_ajustes()
    tipo = tipo_enlace or tipo_enlace_de_ajustes()
    return Sistema(crear_enlace(tipo, ajustes, reloj), reloj, ajustes=ajustes, escucha=escucha)
