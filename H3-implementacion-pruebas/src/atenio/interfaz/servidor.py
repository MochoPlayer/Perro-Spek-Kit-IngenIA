"""Servidor de la página web local (componente 6 de plan.md, D-07). Cubre T056: REQ-19 y REQ-30.

Solo biblioteca estándar y solo en 127.0.0.1. La página pregunta el estado cada poco (sondeo):
GET / (página), GET /estado?desde=N (JSON), GET /nivel?desde=N (onda del micro, solo números),
POST /frase {"texto": ...}, POST /parada, POST /micro {"encender": true|false}.
"""
from __future__ import annotations

import json
import socket
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

        def _desde(self, url) -> int:
            try:
                return max(0, int(parse_qs(url.query).get("desde", ["0"])[0]))
            except ValueError:
                return 0

        def _leer_json(self):
            """El cuerpo JSON como dict, o None si ya se respondió con un error."""
            largo = int(self.headers.get("Content-Length") or 0)
            if largo > MAX_CUERPO:
                self._json({"error": "cuerpo demasiado largo"}, 413)
                return None
            try:
                datos = json.loads(self.rfile.read(largo).decode("utf-8") or "{}")
            except ValueError:
                datos = None
            if not isinstance(datos, dict):
                self._json({"error": "JSON no válido"}, 400)
                return None
            return datos

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/estado":
                self._json(sistema.foto(self._desde(url)))
            elif url.path == "/nivel":
                self._json(sistema.nivel(self._desde(url)))
            else:
                self._json({"error": "no existe"}, 404)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if url.path == "/parada":  # REQ-30
                sistema.pulsar_parada()
                self._json({"ok": True, "parada": sistema.foto(0)["parada"]})
            elif url.path == "/micro":
                datos = self._leer_json()
                if datos is None:
                    return
                encender = datos.get("encender")
                if not isinstance(encender, bool):
                    self._json({"error": "«encender» debe ser true o false"}, 400)
                    return
                self._json({"ok": True, "micro": sistema.poner_micro(encender)})
            elif url.path == "/hablar":  # mantener pulsado el micro
                datos = self._leer_json()
                if datos is None:
                    return
                activo = datos.get("activo")
                if not isinstance(activo, bool):
                    self._json({"error": "«activo» debe ser true o false"}, 400)
                    return
                self._json({"ok": True, "hablando": sistema.hablar(activo)})
            elif url.path == "/frase":
                datos = self._leer_json()
                if datos is None:
                    return
                texto = datos.get("texto", "")
                if not isinstance(texto, str):
                    self._json({"error": "«texto» debe ser texto"}, 400)
                    return
                sistema.oir(texto)
                self._json({"ok": True})
            else:
                self._json({"error": "no existe"}, 404)

    return _ServidorExclusivo((HOST, puerto), Manejador)


class _ServidorExclusivo(ThreadingHTTPServer):
    """En Windows, `allow_reuse_address` deja que dos programas compartan el puerto sin error.
    Aquí el puerto es exclusivo: si está ocupado, falla al arrancar (OSError) en lugar de no recibir nada."""

    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # solo existe en Windows
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def servir_en_hilo(servidor: ThreadingHTTPServer) -> threading.Thread:
    hilo = threading.Thread(target=servidor.serve_forever, name="atenio-web", daemon=True)
    hilo.start()
    return hilo
