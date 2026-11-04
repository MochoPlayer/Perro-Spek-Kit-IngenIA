"""Punto de entrada: `python -m atenio [--simulado | --serie] [--voz] [--puerto N]` (T057 en parte, T058).

Arranca el sistema con el reloj real y sirve la interfaz en http://127.0.0.1:PUERTO/. Ctrl+C para salir.
"""
from __future__ import annotations

import argparse
import importlib
import sys
import webbrowser

from atenio.ajustes import cargar_ajustes
from atenio.interfaz import HOST, crear_servidor
from atenio.principal import crear_sistema

PUERTO_POR_DEFECTO = 8642  # valor de diseño; si está ocupado, --puerto con otro


def leer_opciones(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m atenio", description="Control por voz del Petoi Bittle (di «Perro» y la orden).")
    enlace = p.add_mutually_exclusive_group()
    enlace.add_argument("--simulado", dest="enlace", action="store_const", const="simulado",
                        help="robot simulado (por defecto si ajustes.json no dice otra cosa)")
    enlace.add_argument("--serie", dest="enlace", action="store_const", const="serie",
                        help="robot real por el puerto serie de ajustes.json")
    p.add_argument("--voz", action="store_true", help="arrancar con el micro encendido (sin --voz arranca apagado; se enciende con el botón)")
    p.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO, help=f"puerto web (por defecto {PUERTO_POR_DEFECTO})")
    p.add_argument("--sin-navegador", action="store_true", help="no abrir el navegador al arrancar")
    return p.parse_args(argv)


def crear_escucha_si_hay():
    """--voz: usa atenio.escucha.crear_escucha si el módulo existe; si no, aviso y se sigue sin voz."""
    try:
        modulo = importlib.import_module("atenio.escucha")
    except ImportError as e:
        print(f"Aviso: sin voz (no se puede cargar atenio.escucha: {e}). Usa la caja de texto.", file=sys.stderr)
        return None
    try:
        return modulo.crear_escucha(cargar_ajustes())
    except Exception as e:  # motor no instalado, sin micrófono...: el programa sigue sin voz
        print(f"Aviso: sin voz (no se pudo iniciar la escucha: {e}). Usa la caja de texto.", file=sys.stderr)
        return None


def fabrica_escucha():
    """Para el botón del micro: crea la escucha al primer «encender». Un fallo llega a la interfaz como aviso."""
    return importlib.import_module("atenio.escucha").crear_escucha(cargar_ajustes())


def main(argv: list[str] | None = None) -> int:
    op = leer_opciones(argv)
    # Con --voz el micro arranca encendido; sin --voz, apagado (se enciende con el botón). Decisión de Mario, 04/11.
    escucha = crear_escucha_si_hay() if op.voz else None
    sistema = crear_sistema(op.enlace, escucha=escucha, fabrica_escucha=fabrica_escucha)
    try:
        servidor = crear_servidor(sistema, op.puerto)
    except OSError as e:
        print(f"Error: el puerto {op.puerto} está ocupado o no se puede usar ({e}). Prueba con --puerto 8700.",
              file=sys.stderr)
        return 1
    url = f"http://{HOST}:{servidor.server_address[1]}/"
    sistema.arrancar()
    conectado = "conectado" if sistema.enlace.conectado else "NO conectado"
    print(f"En marcha: {url}  (enlace {op.enlace or 'de ajustes.json'}, robot {conectado}, "
          f"voz {'activa' if sistema.voz_activa else 'apagada'}). Ctrl+C para salir.")
    if not op.sin_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSaliendo…")
    finally:
        servidor.server_close()
        sistema.detener()
    return 0


if __name__ == "__main__":
    sys.exit(main())
