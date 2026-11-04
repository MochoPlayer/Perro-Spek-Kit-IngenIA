"""Panel de botones para probar el Bittle real desde el navegador (bloque C, sesión 2).

No es la interfaz final (esa es T056, bloque A): es una herramienta para mandar comandos con un clic,
ver lo que responde el robot y cronometrar. Solo usa la biblioteca estándar y pyserial.

Uso, desde H3-implementacion-pruebas/:
    python verificacion-robot/panel_robot.py --puerto COM6
    python verificacion-robot/panel_robot.py --simulado          (sin robot, para probar el panel)
y abrir http://localhost:8765
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ_H3 = Path(__file__).resolve().parents[1]
RAIZ_REPO = RAIZ_H3.parent
sys.path.insert(0, str(RAIZ_H3 / "src"))

from atenio.ajustes import cargar_ajustes  # noqa: E402
from atenio.catalogo import cargar_catalogo  # noqa: E402
from atenio.enlace.base import cadena_prohibida  # noqa: E402
from atenio.enlace.serie import EnlaceSerie  # noqa: E402
from atenio.enlace.simulado import EnlaceSimulado  # noqa: E402
from atenio.reloj import RelojReal  # noqa: E402

PAGINA = Path(__file__).with_name("panel_robot.html")
CARPETA_ENSAYOS = RAIZ_REPO / "H4-demostracion-aceptacion" / "ensayos"
FUENTES = next((p.parent for p in (RAIZ_REPO / "identidad-corporativa").rglob("Poppins-Regular.ttf")),
               RAIZ_REPO / "identidad-corporativa" / "fonts")
LOGO = RAIZ_REPO / "identidad-corporativa" / "assets" / "simbolo.svg"

# Comandos de marcha continua: no paran solos (catalogo.json, D-06).
MARCHA = ("kwk", "ktr")


class SimuladoQueResponde(EnlaceSimulado):
    """Para probar el panel sin robot: responde con la primera letra del comando, como el Bittle real."""

    def enviar(self, cadena: str) -> bool:
        ok = super().enviar(cadena)
        if ok:
            threading.Timer(0.3, self.inyectar_linea, args=(cadena[0],)).start()
        return ok


class Panel:
    def __init__(self, enlace, parada: str, reposo: str, descripcion: str) -> None:
        self.enlace = enlace
        self.parada = parada
        self.reposo = reposo
        self.descripcion = descripcion
        self._lock = threading.Lock()
        self._reloj = RelojReal()
        self._inicio = self._reloj.ahora()
        self.eventos: list[dict] = []
        self.medidas: list[dict] = []
        self._ultimo: dict | None = None  # último comando enviado, para cronometrar

    def _evento(self, tipo: str, texto: str, **extra) -> None:
        self.eventos.append({"id": len(self.eventos), "t": round(self._reloj.ahora() - self._inicio, 2),
                             "hora": datetime.now().strftime("%H:%M:%S"), "tipo": tipo, "texto": texto, **extra})

    # ------------------------------------------------------------------ acciones
    def conectar(self) -> bool:
        with self._lock:
            ok = self.enlace.conectado or self.enlace.conectar()
            self._evento("estado", f"conectado a {self.descripcion}" if ok else f"no se pudo conectar a {self.descripcion}")
            return ok

    def desconectar(self) -> None:
        with self._lock:
            self.enlace.desconectar()
            self._evento("estado", "desconectado")

    def enviar(self, comando: str) -> tuple[bool, str]:
        comando = comando.strip()
        if not comando:
            return False, "comando vacío"
        if cadena_prohibida(comando):
            return False, f"«{comando}» está prohibido (giroscopio, D-12)"
        with self._lock:
            if not self.enlace.conectado:
                self._evento("aviso", "robot no conectado")
                return False, "robot no conectado"
            self._cerrar_ultimo("interrumpido por otro comando")
            if not self.enlace.enviar(comando):
                self._evento("aviso", f"no se pudo enviar «{comando}»: se ha perdido la conexión")
                return False, "se ha perdido la conexión"
            self._ultimo = {"comando": comando, "inicio": self._reloj.ahora(), "respuestas": [], "respuesta_s": None}
            self._evento("enviado", comando)
            return True, "enviado"

    def pulsar_parada(self) -> None:
        with self._lock:
            self._cerrar_ultimo("cortado con la parada")
            if self.enlace.conectado and self.enlace.enviar(self.parada):
                self._evento("parada", f"PARADA enviada («{self.parada}»)")
            else:
                self._evento("aviso", "robot no conectado: no se pudo enviar la parada")

    def marcar_fin(self) -> dict | None:
        with self._lock:
            return self._cerrar_ultimo("fin marcado a mano", a_mano=True)

    def leer(self) -> None:
        with self._lock:
            estaba = self.enlace.conectado
            for linea in self.enlace.leer_lineas():
                self._evento("robot", linea)
                if self._ultimo is not None:
                    self._ultimo["respuestas"].append(linea)
                    # Sesión del 04/11: el robot devuelve la primera letra del comando («k», «d»). Con kwkF
                    # llega a los 0,2-0,4 s mientras sigue andando: es un «recibido», NO el fin de la acción.
                    # Se apunta cuánto tarda en llegar; el fin lo marca la persona que observa.
                    u = self._ultimo
                    if u["respuesta_s"] is None and linea.strip() == u["comando"][0]:
                        u["respuesta_s"] = round(self._reloj.ahora() - u["inicio"], 2)
                        self._evento("estado", f"{u['comando']}: el robot respondió «{linea.strip()}» a los {u['respuesta_s']:.2f} s")
            if estaba and not self.enlace.conectado:
                self._evento("aviso", "se ha perdido la conexión con el robot")

    def _cerrar_ultimo(self, nota: str, a_mano: bool = False) -> dict | None:
        if self._ultimo is None:
            return None
        u, self._ultimo = self._ultimo, None
        # Solo «Ha terminado» da una duración. Cortado o interrumpido: se guarda el tiempo que estuvo en marcha.
        tiempo = round(self._reloj.ahora() - u["inicio"], 2)
        medida = {"comando": u["comando"], "respuesta_s": u["respuesta_s"],
                  "duracion_s": tiempo if a_mano else None, "en_marcha_s": None if a_mano else tiempo,
                  "respuestas": list(u["respuestas"]), "nota": nota}
        self.medidas.append(medida)
        texto = f"{u['comando']}: " + (f"duró {tiempo:.2f} s" if a_mano else f"{tiempo:.2f} s en marcha") + f" ({nota})"
        self._evento("medida", texto, **medida)
        return medida

    def guardar_csv(self) -> Path:
        with self._lock:
            CARPETA_ENSAYOS.mkdir(parents=True, exist_ok=True)
            ruta = CARPETA_ENSAYOS / f"panel-{datetime.now():%Y%m%d-%H%M%S}.csv"
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["comando", "respuesta_s", "duracion_s", "en_marcha_s", "respuestas", "nota"])
                for m in self.medidas:
                    f2 = lambda v: "" if v is None else f"{v:.2f}"  # noqa: E731
                    w.writerow([m["comando"], f2(m["respuesta_s"]), f2(m["duracion_s"]), f2(m["en_marcha_s"]),
                                " | ".join(m["respuestas"]), m["nota"]])
            self._evento("estado", f"medidas guardadas en {ruta.relative_to(RAIZ_REPO)}")
            return ruta

    def estado(self, desde: int) -> dict:
        with self._lock:
            return {
                "conectado": self.enlace.conectado,
                "descripcion": self.descripcion,
                "en_curso": None if self._ultimo is None else {
                    "comando": self._ultimo["comando"],
                    "respuesta_s": self._ultimo["respuesta_s"],
                    "segundos": round(self._reloj.ahora() - self._ultimo["inicio"], 1)},
                "eventos": self.eventos[desde:],
            }


def botones() -> list[dict]:
    """Órdenes de Nivel 1 del catálogo, más el reposo. Los nombres salen de catalogo.json."""
    datos = json.loads((RAIZ_H3 / "datos" / "catalogo.json").read_text(encoding="utf-8"))
    lista = []
    for o in datos["ordenes"]:
        if o.get("nivel") != 1 or not o.get("pasos"):
            continue
        comando = o["pasos"][0]["comando"]
        lista.append({"id": o["id"], "nombre": o["nombre"], "comando": comando,
                      "grupo": "movimiento" if comando.startswith(MARCHA) else "postura"})
    return lista


def crear_manejador(panel: Panel):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *_):  # sin ruido en la consola
            pass

        def _json(self, datos, codigo=200):
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _fichero(self, ruta: Path, tipo: str):
            if not ruta.is_file():
                self.send_error(404)
                return
            cuerpo = ruta.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            ruta = self.path.split("?")[0]
            if ruta == "/":
                self._fichero(PAGINA, "text/html; charset=utf-8")
            elif ruta == "/logo.svg":
                self._fichero(LOGO, "image/svg+xml")
            elif ruta.startswith("/fuentes/") and ruta.endswith(".ttf"):
                self._fichero(FUENTES / Path(ruta).name, "font/ttf")
            elif ruta == "/botones":
                self._json({"botones": botones(), "parada": panel.parada, "reposo": panel.reposo})
            elif ruta == "/estado":
                try:
                    desde = int(self.path.split("desde=")[1]) if "desde=" in self.path else 0
                except ValueError:
                    desde = 0
                self._json(panel.estado(desde))
            else:
                self.send_error(404)

        def do_POST(self):
            largo = int(self.headers.get("Content-Length") or 0)
            datos = json.loads(self.rfile.read(largo) or b"{}") if largo else {}
            if self.path == "/enviar":
                ok, texto = panel.enviar(str(datos.get("comando", "")))
                self._json({"ok": ok, "texto": texto}, 200 if ok else 400)
            elif self.path == "/parada":
                panel.pulsar_parada()
                self._json({"ok": True})
            elif self.path == "/fin":
                self._json({"ok": True, "medida": panel.marcar_fin()})
            elif self.path == "/conectar":
                self._json({"ok": panel.conectar()})
            elif self.path == "/desconectar":
                panel.desconectar()
                self._json({"ok": True})
            elif self.path == "/guardar":
                self._json({"ok": True, "ruta": str(panel.guardar_csv().relative_to(RAIZ_REPO))})
            else:
                self.send_error(404)

    return Manejador


def main(argv: list[str] | None = None) -> int:
    ajustes = cargar_ajustes()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--puerto", default=ajustes.puerto, help="p. ej. COM6")
    p.add_argument("--baudios", type=int, default=ajustes.baudios)
    p.add_argument("--simulado", action="store_true", help="sin robot: robot simulado")
    p.add_argument("--web", type=int, default=8765, help="puerto de la página (por defecto 8765)")
    args = p.parse_args(argv)

    if args.simulado:
        enlace, descripcion = SimuladoQueResponde(RelojReal(), conectado=False), "robot simulado"
    elif args.puerto:
        enlace, descripcion = EnlaceSerie(args.puerto, args.baudios, ajustes.fin_de_linea), args.puerto
    else:
        print("Falta --puerto (p. ej. --puerto COM6) o --simulado.")
        return 2

    panel = Panel(enlace, ajustes.comando_parada, ajustes.comando_reposo, descripcion)
    panel.conectar()

    parar = threading.Event()

    def lector():
        while not parar.is_set():
            panel.leer()
            time.sleep(0.05)

    threading.Thread(target=lector, daemon=True).start()
    servidor = ThreadingHTTPServer(("127.0.0.1", args.web), crear_manejador(panel))
    print(f"Panel en http://localhost:{args.web}  ·  robot: {descripcion}  ·  Ctrl+C para salir")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nSaliendo: envío la parada.")
        panel.pulsar_parada()
    finally:
        parar.set()
        servidor.server_close()
        if panel.medidas:
            print(f"Medidas guardadas en {panel.guardar_csv()}")
        enlace.desconectar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
