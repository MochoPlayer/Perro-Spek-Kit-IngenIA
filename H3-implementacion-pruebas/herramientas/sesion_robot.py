"""Consola para la sesión 2 con el Bittle real (T068 a T071 y T080). No forma parte del programa final.

Uso, desde H3-implementacion-pruebas/:
    python herramientas/sesion_robot.py --listar
    python herramientas/sesion_robot.py --puerto COM5
    python herramientas/sesion_robot.py --puerto COM5 --baudios 115200 --fin "\\n"

Dentro de la consola:
    ksit       envía el comando y empieza a cronometrar
    (Enter)    el robot ha terminado: guarda la duración
    -          el comando no termina solo (marcha continua): guarda sin duración
    p          PARADA: envía el comando de parada de ajustes.json
    n texto    añade una nota a la última medida
    l          muestra lo que ha enviado el robot
    q          sale y guarda el CSV
Ctrl+C también envía la parada antes de salir.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

RAIZ_H3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ_H3 / "src"))

from atenio.ajustes import cargar_ajustes  # noqa: E402
from atenio.catalogo import cargar_catalogo  # noqa: E402
from atenio.enlace.medicion import ErrorMedicion, SesionMedida, interpretar_fin_de_linea  # noqa: E402
from atenio.enlace.serie import EnlaceSerie  # noqa: E402
from atenio.reloj import RelojReal  # noqa: E402

CARPETA_ENSAYOS = RAIZ_H3.parent / "H4-demostracion-aceptacion" / "ensayos"

LISTA_SEGURIDAD = (  # T068, REQ-28
    "El robot está sobre una superficie lisa y sin obstáculos",
    "Hay una persona vigilando el robot todo el tiempo",
    "La batería está cargada",
)


def listar_puertos() -> None:
    from serial.tools import list_ports

    puertos = list(list_ports.comports())
    if not puertos:
        print("No se ve ningún puerto serie. Conecta el robot (USB) o empareja el Bluetooth.")
    for p in puertos:
        print(f"{p.device:10} {p.description}")


def lista_seguridad() -> bool:
    print("\nLista de seguridad (T068). Responde s/n:")
    for punto in LISTA_SEGURIDAD:
        if input(f"  · {punto}: ").strip().lower() not in ("s", "si", "sí"):
            print("No se empieza la sesión hasta que se cumpla todo.")
            return False
    return True


def main(argv: list[str] | None = None) -> int:
    ajustes = cargar_ajustes()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listar", action="store_true", help="lista los puertos serie y sale")
    parser.add_argument("--puerto", default=ajustes.puerto, help="p. ej. COM5 (por defecto, el de ajustes.json)")
    parser.add_argument("--baudios", type=int, default=ajustes.baudios)
    parser.add_argument("--fin", default=None, help='fin de línea: "\\n", "\\r\\n" o "ninguno"')
    parser.add_argument("--salida", type=Path, default=None, help="CSV donde guardar las medidas")
    args = parser.parse_args(argv)

    if args.listar:
        listar_puertos()
        return 0
    if not args.puerto:
        print("Falta --puerto. Usa --listar para ver cuál es.")
        return 2

    fin = ajustes.fin_de_linea if args.fin is None else interpretar_fin_de_linea(args.fin)
    salida = args.salida or CARPETA_ENSAYOS / f"sesion-{datetime.now():%Y%m%d-%H%M}.csv"
    comandos_catalogo = {p.comando for o in cargar_catalogo().ordenes for p in o.pasos}
    parada = ajustes.comando_parada

    if not lista_seguridad():
        return 1

    enlace = EnlaceSerie(args.puerto, args.baudios, fin)
    if not enlace.conectar():
        print(f"No se pudo abrir {args.puerto} a {args.baudios} baudios.")
        return 1
    print(f"Conectado a {args.puerto} ({args.baudios} baudios, fin de línea {fin!r}). Parada: «{parada}».")
    sesion = SesionMedida(enlace, RelojReal())

    try:
        while True:
            entrada = input("en curso> " if sesion.en_curso else "> ").strip()
            for linea in sesion.leer():
                print(f"  robot: {linea}")
            try:
                if entrada == "q":
                    break
                if entrada == "p":
                    if sesion.en_curso:
                        sesion.terminar(nota="cortado con la parada")
                    enlace.enviar(parada)
                    print(f"  parada enviada («{parada}»)")
                elif entrada == "" and sesion.en_curso:
                    m = sesion.terminar()
                    print(f"  {m.comando}: {m.duracion_s:.2f} s · respuestas: {m.respuestas or '—'}")
                elif entrada == "-" and sesion.en_curso:
                    m = sesion.terminar(None, nota="no termina solo")
                    print(f"  {m.comando}: sin duración (no termina solo)")
                elif entrada.startswith("n ") and sesion.medidas:
                    sesion.medidas[-1].nota = (sesion.medidas[-1].nota + " " + entrada[2:]).strip()
                elif entrada == "l":
                    pass  # las líneas ya se han mostrado arriba
                elif entrada:
                    if entrada not in comandos_catalogo and entrada != parada:
                        print(f"  aviso: «{entrada}» no está en catalogo.json")
                    sesion.enviar(entrada)
                    print("  enviado. Enter cuando termine, «-» si no termina solo, «p» para parar.")
            except ErrorMedicion as error:
                print(f"  error: {error}")
                if not enlace.conectado:
                    print("  se ha perdido la conexión; se guarda lo medido.")
                    break
    except KeyboardInterrupt:
        print("\nCtrl+C: envío la parada.")
        enlace.enviar(parada)
    finally:
        if sesion.en_curso:
            sesion.terminar(None, nota="sesión terminada con el comando en curso")
        if sesion.medidas:
            print(f"Medidas guardadas en {sesion.guardar_csv(salida)}")
        enlace.desconectar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
