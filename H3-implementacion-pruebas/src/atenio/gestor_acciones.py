"""Gestor de acciones (componente 4 de plan.md): cola, fin de acción, «para», parada de emergencia y reposo.

Cubre REQ-07, REQ-25, REQ-29 a REQ-33 con D-06, D-08, D-10, D-11 y D-13. Sin hilos ni esperas: avanza con tick().
"""
from __future__ import annotations

from collections import deque
from enum import Enum

from atenio.ajustes import Ajustes, cargar_ajustes
from atenio.enlace.base import Enlace, es_bateria_baja
from atenio.eventos import (
    AVISO_BATERIA_BAJA,
    AVISO_CONEXION_PERDIDA,
    AVISO_NO_CONECTADO,
    AVISO_PARADA_ACTIVA,
    Eventos,
    TipoEvento,
)
from atenio.modelos import Interpretacion, Paso, TipoInterpretacion
from atenio.reloj import Reloj


class Estado(Enum):
    """Estados del diagrama de plan.md, «Estados del gestor de acciones»."""

    LIBRE = "Libre"
    OCUPADO = "Ocupado"
    REPOSO = "Reposo"
    PARADA = "Parada"


# Textos del evento ESTADO_CONEXION (T060, REQ-19): la interfaz los muestra tal cual.
ESTADO_CONECTADO = "conectado"
ESTADO_DESCONECTADO = "desconectado"


def aviso_duracion_sin_medir(comando: str) -> str:
    """P-03: el catálogo no tiene la duración de este comando."""
    return f"duración de «{comando}» sin medir: las órdenes en cola esperan a «para» o al botón de parada"


class GestorAcciones:
    """Recibe interpretaciones y el botón de parada; envía cadenas al enlace y publica eventos.

    Fin de acción (D-06): un paso termina cuando pasa su duración estimada del catálogo.
    Duración `None` (sin medir, P-03): el paso no termina solo. Es la opción segura: no se envía el
    siguiente comando sin saber si el anterior acabó. Lo cortan «para», el botón o el reposo por
    inactividad. `duracion_desconocida_s` permite fijar un valor cuando el equipo lo decida.
    """

    def __init__(
        self,
        enlace: Enlace,
        reloj: Reloj,
        eventos: Eventos | None = None,
        ajustes: Ajustes | None = None,
        *,
        inactividad_s: float | None = None,
        duracion_desconocida_s: float | None = None,
    ) -> None:
        self._enlace = enlace
        self._reloj = reloj
        self.eventos = eventos if eventos is not None else Eventos()
        self._ajustes = ajustes if ajustes is not None else cargar_ajustes()
        # REQ-31: T de la demostración salvo que se pida otro (uso real: ajustes.inactividad_real_s).
        self._inactividad_s = inactividad_s if inactividad_s is not None else self._ajustes.inactividad_demo_s
        self._duracion_desconocida_s = duracion_desconocida_s

        self.estado = Estado.LIBRE
        self._cola: deque[Paso] = deque()
        self._seguimiento: deque[tuple[int, str]] = deque()  # (n.º de orden, id) de cada paso de la cola
        self._n_orden = 0
        self.ejecutadas: list[str] = []  # ids de las órdenes cuyo último paso ya se envió, en orden
        self._fin_paso: float | None = None  # hora estimada de fin del paso en curso (None = sin medir)
        self._ultima_orden = reloj.ahora()  # REQ-31: hora de la última orden válida
        self._ultimo_envio: float | None = None
        # T060: último estado de conexión conocido; tick() publica un evento cuando cambia.
        self._conexion_conocida = enlace.conectado

    # ------------------------------------------------------------------ consultas

    @property
    def cola(self) -> tuple[Paso, ...]:
        """Pasos que esperan (sin contar el que está en curso)."""
        return tuple(self._cola)

    @property
    def cola_ordenes(self) -> tuple[str, ...]:
        """Ids de las órdenes que aún tienen pasos en la cola, en orden (una vez por orden)."""
        vistas: list[tuple[int, str]] = []
        for numero, id_orden in self._seguimiento:
            if not vistas or vistas[-1][0] != numero:
                vistas.append((numero, id_orden))
        return tuple(i for _, i in vistas)

    def _vaciar_cola(self) -> None:
        self._cola.clear()
        self._seguimiento.clear()

    @property
    def ultimo_envio(self) -> float | None:
        return self._ultimo_envio

    # ------------------------------------------------------------------ conexión (T060)

    def conectar(self) -> bool:
        """Abre el enlace y publica el estado de conexión (REQ-19). Si no conecta, avisa (REQ-25)."""
        conectado = self._enlace.conectar()
        self._publicar_conexion(conectado)
        if not conectado:
            self._avisar(AVISO_NO_CONECTADO)
        return conectado

    def publicar_estado_conexion(self) -> None:
        """Publica el estado actual, p. ej. cuando la interfaz se abre y necesita mostrarlo (REQ-19)."""
        self._publicar_conexion(self._enlace.conectado)

    # ------------------------------------------------------------------ entradas

    def recibir(self, interpretacion: Interpretacion) -> None:
        """Atiende la salida del intérprete. Solo el tipo ORDENES puede producir comandos."""
        for aviso in interpretacion.avisos:  # REQ-12, REQ-13, REQ-29: avisos del intérprete
            self._avisar(aviso)
        if interpretacion.tipo is not TipoInterpretacion.ORDENES or not interpretacion.ordenes:
            return

        if self.estado is Estado.PARADA:  # REQ-30: manda sobre todo lo demás
            self._avisar(AVISO_PARADA_ACTIVA)
            return
        if not self._enlace.conectado:  # REQ-25
            self._avisar(AVISO_NO_CONECTADO)
            return

        self._ultima_orden = self._reloj.ahora()
        for orden in interpretacion.ordenes:
            self.eventos.publicar(TipoEvento.ORDEN_INTERPRETADA, orden.id)
            if orden.interrumpe:  # REQ-07, D-10: «para» no se encola
                self._para(orden.pasos, orden.id)
                if self.estado is not Estado.LIBRE:
                    return
                continue
            self._n_orden += 1
            self._cola.extend(orden.pasos)  # REQ-29, REQ-32: orden dicho / de llegada
            self._seguimiento.extend((self._n_orden, orden.id) for _ in orden.pasos)
        if self._cola and self.estado in (Estado.LIBRE, Estado.REPOSO):
            self._enviar_siguiente()

    def pulsar_parada(self) -> None:
        """Botón de parada de emergencia (REQ-30). Un clic activa; el siguiente desactiva."""
        if self.estado is Estado.PARADA:
            self.estado = Estado.LIBRE
            self._ultima_orden = self._reloj.ahora()
            return
        self._vaciar_cola()
        self._fin_paso = None
        self.estado = Estado.PARADA
        self._avisar(AVISO_PARADA_ACTIVA)
        if self._enlace.conectado:
            self._enviar(self._ajustes.comando_parada)  # D-11: `d` (discrepancia Y-03)
        else:
            self._avisar(AVISO_NO_CONECTADO)

    def tick(self) -> None:
        """Avanza el gestor hasta la hora del reloj: líneas del robot, fin de pasos y reposo."""
        for linea in self._enlace.leer_lineas():
            if es_bateria_baja(linea):  # REQ-33
                self._avisar(AVISO_BATERIA_BAJA)

        ahora = self._reloj.ahora()
        while self.estado is Estado.OCUPADO and self._fin_paso is not None and ahora >= self._fin_paso:
            if self._cola:
                self._enviar_siguiente()
            else:
                self._fin_paso = None
                self.estado = Estado.LIBRE

        if self._toca_reposo(ahora):  # REQ-31
            self._reposo_por_inactividad()

        if self._enlace.conectado != self._conexion_conocida:  # T060: p. ej. cable desconectado
            self._publicar_conexion(self._enlace.conectado)

    # ------------------------------------------------------------------ interno

    def _toca_reposo(self, ahora: float) -> bool:
        if ahora - self._ultima_orden < self._inactividad_s or not self._enlace.conectado:
            return False
        if self.estado is Estado.LIBRE:
            return True
        # P-03: un paso sin duración no termina solo; el reposo por inactividad lo corta.
        return self.estado is Estado.OCUPADO and self._fin_paso is None

    def _reposo_por_inactividad(self) -> None:
        self._vaciar_cola()
        self._fin_paso = None
        if self._enviar(self._ajustes.comando_reposo):  # sin aviso (REQ-31)
            self.estado = Estado.REPOSO

    def _para(self, pasos: tuple[Paso, ...], id_orden: str | None = None) -> None:
        """«Para» (REQ-07, D-10): envía sus comandos del catálogo (`krest`) aunque haya acción en curso."""
        if self._ajustes.para_vacia_cola:  # OPEN-12, opción A
            self._vaciar_cola()
        self._fin_paso = None
        self.estado = Estado.LIBRE
        for paso in pasos:
            if not self._enviar(paso.comando):
                return
        if id_orden is not None:
            self.ejecutadas.append(id_orden)
        if self._cola:  # opción B: la cola sigue tras la parada
            self._enviar_siguiente()

    def _enviar_siguiente(self) -> None:
        paso = self._cola.popleft()
        numero, id_orden = self._seguimiento.popleft()
        if not self._enviar(paso.comando):
            return
        if not self._seguimiento or self._seguimiento[0][0] != numero:  # era el último paso de su orden
            self.ejecutadas.append(id_orden)
        self.estado = Estado.OCUPADO
        duracion = paso.duracion_s if paso.duracion_s is not None else self._duracion_desconocida_s
        if duracion is None:
            self._fin_paso = None
            if self._cola:
                self._avisar(aviso_duracion_sin_medir(paso.comando))
        else:
            self._fin_paso = self._reloj.ahora() + duracion

    def _enviar(self, comando: str) -> bool:
        """Envía una cadena. Si falla, D-13: desconectado, cola vacía y aviso (P-08)."""
        if self._enlace.enviar(comando):
            self._ultimo_envio = self._reloj.ahora()
            return True
        self._enlace.desconectar()
        self._vaciar_cola()
        self._fin_paso = None
        if self.estado is not Estado.PARADA:
            self.estado = Estado.LIBRE
        self._publicar_conexion(False)
        self._avisar(AVISO_CONEXION_PERDIDA)
        return False

    def _publicar_conexion(self, conectado: bool) -> None:
        self._conexion_conocida = conectado
        texto = ESTADO_CONECTADO if conectado else ESTADO_DESCONECTADO
        self.eventos.publicar(TipoEvento.ESTADO_CONEXION, texto)

    def _avisar(self, texto: str) -> None:
        self.eventos.publicar(TipoEvento.AVISO, texto)
