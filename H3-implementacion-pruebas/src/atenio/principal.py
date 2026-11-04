"""Arranque del sistema (componente 1 de plan.md): catálogo → intérprete → gestor → enlace → eventos.

Cubre T019, T045 y parte de T057 (REQ-19, REQ-26, REQ-27). La voz es opcional: `escucha` sigue el contrato de
`atenio.escucha` (iniciar(al_oir), parar(), activa) por tipado de pato. Sin voz, las frases llegan por `oir()`.
El botón del micro de la interfaz usa `poner_micro()`; si aún no hay escucha, la crea con `fabrica_escucha`.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable

from atenio.ajustes import RUTA_POR_DEFECTO as RUTA_AJUSTES
from atenio.ajustes import Ajustes, cargar_ajustes
from atenio.catalogo import Catalogo, cargar_catalogo, normalizar
from atenio.enlace.base import Enlace
from atenio.enlace.serie import EnlaceSerie
from atenio.enlace.simulado import EnlaceSimulado
from atenio.eventos import Evento, Eventos, TipoEvento
from atenio.gestor_acciones import GestorAcciones
from atenio.interprete import AVISO_NO_DISPONIBLE, AVISO_NO_ENTENDIDA, Interprete
from atenio.reloj import Reloj, RelojReal

TIPOS_ENLACE = ("simulado", "serie")
AVISO_SIN_VOZ = "no hay voz en este programa: usa la caja de texto"  # texto provisional
PERIODO_TICK_S = 0.05  # cada cuánto avanza el gestor con el reloj real (valor de diseño, no medido)
# Cómo transcribe Vosk la palabra de activación (prueba del 04/11: «Perro, siéntate» → «pero siéntate»).
# Solo se usa en modo «pulsar», donde pulsar ya es llamar al robot: en modo continuo «pero» daría falsas activaciones.
OIDO_COMO_ACTIVACION = {"perro": ("pero", "perro", "perra", "perros")}


def tipo_enlace_de_ajustes(ruta: str | Path | None = None) -> str:
    """T045: lee la clave «enlace» de ajustes.json («simulado» si no está)."""
    datos = json.loads(Path(ruta or RUTA_AJUSTES).read_text(encoding="utf-8"))
    tipo = datos.get("enlace", {}).get("valor", "simulado")
    if tipo not in TIPOS_ENLACE:
        raise ValueError(f"enlace desconocido en ajustes.json: «{tipo}» (valores: {', '.join(TIPOS_ENLACE)})")
    return tipo


def crear_enlace(tipo: str, ajustes: Ajustes, reloj: Reloj, puerto: str | None = None) -> Enlace:
    """T045, D-03: el mismo programa con el robot simulado o con el puerto serie real.

    `puerto` (opción --com) manda sobre el de ajustes.json: el número COM cambia en cada ordenador.
    """
    if tipo == "simulado":
        return EnlaceSimulado(reloj)
    if tipo == "serie":
        return EnlaceSerie(puerto or ajustes.puerto, ajustes.baudios, ajustes.fin_de_linea,
                           espera_arranque_s=ajustes.espera_arranque_robot_s,
                           tope_abrir_s=ajustes.tope_abrir_puerto_s)
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
        fabrica_escucha: Callable[[], object] | None = None,
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
            palabras_activacion=(self.ajustes.palabra_activacion,),
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
        self._fabrica_escucha = fabrica_escucha  # crea la escucha al primer «encender» (programa sin --voz)
        self._cerrojo_micro = threading.Lock()  # encender y apagar no se pisan (cargar el modelo tarda)
        self.cerrojo = threading.RLock()
        self._parar = threading.Event()
        self._hilo: threading.Thread | None = None

    # ------------------------------------------------------------------ entradas

    def oir(self, texto: str) -> None:
        """Una frase (de la voz o de la caja de texto): evento «texto reconocido» y al intérprete."""
        texto = texto.strip()
        if not texto:
            return
        if self._pulsando():  # pulsar ya es llamar al robot: no hace falta decir la palabra de activación
            palabra = self.ajustes.palabra_activacion
            palabras = texto.split()
            # Vosk (modelo pequeño) oye «perro» como «pero» (prueba del 04/11): si la frase empieza así, se quita.
            if len(palabras) > 1 and normalizar(palabras[0]) in OIDO_COMO_ACTIVACION.get(normalizar(palabra), ()):
                texto = " ".join(palabras[1:])
            if normalizar(texto.split()[0]) != normalizar(palabra):
                texto = f"{palabra} {texto}"
        with self.cerrojo:
            self.eventos.publicar(TipoEvento.TEXTO_RECONOCIDO, texto)
            self.gestor.recibir(self.interprete.interpretar(texto))

    def _pulsando(self) -> bool:
        """True si la escucha está en modo «pulsar» (la voz no necesita la palabra de activación)."""
        return self.voz_activa and getattr(self.escucha, "modo", None) == "pulsar"

    def hablar(self, activo: bool) -> bool:
        """Mantener pulsado el micro (True) o soltarlo (False). Devuelve si se está grabando."""
        pulsar = getattr(self.escucha, "pulsar", None)
        if pulsar is not None and self.voz_activa:
            pulsar(activo)
        return bool(getattr(self.escucha, "hablando", False)) and self.voz_activa

    def pulsar_parada(self) -> None:
        """Botón de parada de emergencia (REQ-30)."""
        with self.cerrojo:
            self.gestor.pulsar_parada()

    def poner_micro(self, encender: bool) -> bool:
        """Botón del micro: enciende o apaga la escucha. Devuelve si queda escuchando. Un fallo sale como aviso."""
        with self._cerrojo_micro:
            if not encender:
                if self.escucha is not None:
                    self.escucha.parar()
                return self.voz_activa
            if self.escucha is None:
                if self._fabrica_escucha is None:
                    self._avisar(AVISO_SIN_VOZ)
                    return False
                try:
                    self.escucha = self._fabrica_escucha()
                except Exception as e:  # motor no instalado, falta el modelo...
                    self._avisar(f"no se pudo encender el micro: {e}")
                    return False
            if not self.voz_activa:
                self.escucha.iniciar(self.oir)
            return self.voz_activa

    def _avisar(self, texto: str) -> None:
        with self.cerrojo:
            self.eventos.publicar(TipoEvento.AVISO, texto)

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

    @property
    def tipo_enlace(self) -> str:
        """«simulado», «serie» u otro: el nombre de la clase del enlace sin «Enlace»."""
        return type(self.enlace.interno).__name__.removeprefix("Enlace").lower() or "desconocido"

    def nivel(self, desde: int = 0) -> dict:
        """Niveles (RMS) del micrófono desde el número `desde`, para la onda. Solo números (REQ-24)."""
        medidor = getattr(self.escucha, "nivel", None) if self.voz_activa else None
        if medidor is None:
            return {"activo": False, "umbral": None, "valores": [], "total": desde, "modo": None, "hablando": False}
        valores, total = medidor.desde(desde)
        return {"activo": True, "umbral": medidor.umbral, "valores": valores, "total": total,
                "modo": getattr(self.escucha, "modo", "continuo"), "hablando": bool(getattr(self.escucha, "hablando", False))}

    def foto(self, desde: int = 0) -> dict:
        """Estado actual y eventos a partir del número `desde` (para la interfaz)."""
        with self.cerrojo:
            eventos = self.eventos.lista[desde:]
            return {
                "estado": self.gestor.estado.value,
                "conectado": self.enlace.conectado,
                "parada": self.gestor.estado.value == "Parada",
                "voz_activa": self.voz_activa,
                "error_voz": self._error_voz(),
                "enlace": self.tipo_enlace,
                "cola": len(self.gestor.cola),
                "cola_ordenes": [self._palabra(i) for i in self.gestor.cola_ordenes],
                "ejecutadas": [{"palabra": self._palabra(i), "comandos": self._comandos(i)}
                               for i in reversed(self.gestor.ejecutadas[-50:])],
                "desde": desde,
                "total_eventos": desde + len(eventos),
                "eventos": [{"tipo": e.tipo.value, "texto": self._para_pantalla(e), "hora": h,
                             "oculto": self._no_reconocida(e), **self._orden(e)}
                            for e, h in zip(eventos, self._horas[desde:])],
                "registro": [{"t": round(t - self._inicio, 2), "comando": c} for t, c in self.enlace.registro[-50:]],
            }

    @staticmethod
    def _no_reconocida(e: Evento) -> bool:
        """Los avisos de órdenes no reconocidas no se enseñan en la pantalla (petición de Mario, 04/11)."""
        return e.tipo is TipoEvento.AVISO and (
            e.texto.startswith(AVISO_NO_ENTENDIDA) or e.texto.startswith(AVISO_NO_DISPONIBLE)
        )

    def _palabra(self, id_orden: str) -> str:
        try:
            return self.catalogo.por_id(id_orden).palabras[0]
        except (KeyError, IndexError, ValueError):
            return id_orden

    def _comandos(self, id_orden: str) -> list[str]:
        try:
            return [p.comando for p in self.catalogo.por_id(id_orden).pasos]
        except (KeyError, ValueError):
            return []

    def _error_voz(self) -> str | None:
        error = getattr(self.escucha, "error", None)
        return str(error) if error is not None and not self.voz_activa else None

    def _orden(self, e: Evento) -> dict:
        """Para la lista de la interfaz: la orden interpretada con su palabra del catálogo y sus comandos."""
        if e.tipo is not TipoEvento.ORDEN_INTERPRETADA:
            return {}
        try:
            orden = self.catalogo.por_id(e.texto)
        except (KeyError, ValueError):
            return {}
        return {"orden": {"palabra": orden.palabras[0], "comandos": [p.comando for p in orden.pasos]}}

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


def crear_sistema(
    tipo_enlace: str | None = None, *, escucha=None, fabrica_escucha=None, reloj: Reloj | None = None,
    puerto_robot: str | None = None,
) -> Sistema:
    """Monta el sistema con el reloj real y el enlace de ajustes.json (o el que se pida)."""
    reloj = reloj if reloj is not None else RelojReal()
    ajustes = cargar_ajustes()
    tipo = tipo_enlace or ("serie" if puerto_robot else tipo_enlace_de_ajustes())
    return Sistema(crear_enlace(tipo, ajustes, reloj, puerto_robot), reloj, ajustes=ajustes, escucha=escucha,
                   fabrica_escucha=fabrica_escucha)
