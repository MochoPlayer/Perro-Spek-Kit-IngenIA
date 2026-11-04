# Carga de ajustes.json (plan.md, «Ajustes»). Cubre REQ-31, REQ-35, OPEN-02, OPEN-07, OPEN-11.
# `palabra_activacion`: el nombre que hay que decir antes de la orden (REQ-01; «perro» desde el 04/11).
# La sección «voz» (motor, micrófono, cortes de frase; P-01) la usa escucha.py.
import json
from dataclasses import dataclass, field
from pathlib import Path

PALABRA_POR_DEFECTO = "perro"  # solo si ajustes.json no trae la clave
RUTA_POR_DEFECTO = Path(__file__).resolve().parents[2] / "datos" / "ajustes.json"


@dataclass(frozen=True)
class Ajustes:
    espera_orden_s: float
    inactividad_demo_s: float
    inactividad_real_s: float
    comando_reposo: str
    comando_parada: str
    puerto: str | None
    baudios: int
    max_ordenes_por_frase: int | None
    para_vacia_cola: bool
    fin_de_linea: str
    provisionales: tuple[str, ...]  # claves marcadas «provisional»
    voz: dict = field(default_factory=dict)  # sección «voz» (escucha.py); vacía si falta
    palabra_activacion: str = PALABRA_POR_DEFECTO  # REQ-01, REQ-35
    # True: cada orden nueva corta la acción en curso y se ejecuta ya (decisión del equipo, 04/11; cambia REQ-32).
    # False: cola en orden de llegada (REQ-32 tal como está en spec.md).
    nueva_orden_interrumpe: bool = False
    espera_arranque_robot_s: float = 0.0  # al abrir el puerto el Bittle se reinicia; se espera su «Ready!»
    tope_abrir_puerto_s: float | None = None  # sin robot encendido, abrir el COM de Bluetooth no vuelve nunca


def cargar_ajustes(ruta: str | Path | None = None) -> Ajustes:
    datos = json.loads(Path(ruta or RUTA_POR_DEFECTO).read_text(encoding="utf-8"))

    def v(clave: str):
        return datos[clave]["valor"]

    return Ajustes(
        espera_orden_s=float(v("espera_orden_s")),
        inactividad_demo_s=float(v("inactividad_demo_s")),
        inactividad_real_s=float(v("inactividad_real_s")),
        comando_reposo=v("comando_reposo"),
        comando_parada=v("comando_parada"),
        puerto=v("puerto"),
        baudios=int(v("baudios")),
        max_ordenes_por_frase=v("max_ordenes_por_frase"),
        para_vacia_cola=bool(v("para_vacia_cola")),
        fin_de_linea=v("fin_de_linea"),
        provisionales=tuple(k for k, e in datos.items() if e.get("provisional")),
        voz=dict(v("voz")) if "voz" in datos else {},
        palabra_activacion=str(v("palabra_activacion")) if "palabra_activacion" in datos else PALABRA_POR_DEFECTO,
        nueva_orden_interrumpe=bool(v("nueva_orden_interrumpe")) if "nueva_orden_interrumpe" in datos else False,
        espera_arranque_robot_s=float(v("espera_arranque_robot_s")) if "espera_arranque_robot_s" in datos else 0.0,
        tope_abrir_puerto_s=float(v("tope_abrir_puerto_s")) if datos.get("tope_abrir_puerto_s", {}).get("valor") is not None else None,
    )
