"""Servidor de la página web local (componente 6 de plan.md, D-07). Cubre T056: REQ-19 y REQ-30.

Solo biblioteca estándar y solo en 127.0.0.1. La página pregunta el estado cada poco (sondeo):
GET / (página), GET /estado?desde=N (JSON), POST /frase {"texto": ...}, POST /parada.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PAGINA = Path(__file__).with_name("pagina.html")
HOST = "127.0.0.1"  # solo el propio portátil: sin red (REQ-27)
MAX_CUERPO = 4096  # bytes; una frase no necesita más


def crear_servidor(sistema, puerto: int = 0) -> ThreadingHTTPServer:
    """Servidor sin arrancar. `puerto=0` elige uno libre (pruebas). El puerto real: `servidor.server_address[1]`."""

    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # sin ruido en la consola
            pass

        def _responder(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def _json(self, datos: dict, codigo: int = 200) -> None:
            self._responder(codigo, json.dumps(datos, ensure_ascii=False).encode("utf-8"),
                            "application/json; charset=utf-8")

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/estado":
                try:
                    desde = max(0, int(parse_qs(url.query).get("desde", ["0"])[0]))
                except ValueError:
                    desde = 0
                self._json(sistema.foto(desde))
            else:
                self._json({"error": "no existe"}, 404)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if url.path == "/parada":  # REQ-30
                sistema.pulsar_parada()
                self._json({"ok": True, "parada": sistema.foto(0)["parada"]})
            elif url.path == "/frase":
                largo = int(self.headers.get("Content-Length") or 0)
                if largo > MAX_CUERPO:
                    self._json({"error": "frase demasiado larga"}, 413)
                    return
                try:
                    texto = json.loads(self.rfile.read(largo).decode("utf-8") or "{}").get("texto", "")
                except (ValueError, AttributeError):
                    self._json({"error": "JSON no válido"}, 400)
                    return
                if not isinstance(texto, str):
                    self._json({"error": "«texto» debe ser texto"}, 400)
                    return
                sistema.oir(texto)
                self._json({"ok": True})
            else:
                self._json({"error": "no existe"}, 404)

    servidor = ThreadingHTTPServer((HOST, puerto), Manejador)
    servidor.daemon_threads = True
    return servidor


def servir_en_hilo(servidor: ThreadingHTTPServer) -> threading.Thread:
    hilo = threading.Thread(target=servidor.serve_forever, name="atenio-web", daemon=True)
    hilo.start()
    return hilo
