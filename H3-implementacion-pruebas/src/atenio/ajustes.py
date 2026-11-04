# Carga de ajustes.json (plan.md, «Ajustes»). Cubre REQ-31, REQ-35, OPEN-02, OPEN-07, OPEN-11.
import json
from dataclasses import dataclass
from pathlib import Path

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
    )
