"""Claude Bridge: servidor local que permite a Claude ejecutar Python dentro de Blender.

Escucha solo en 127.0.0.1. Cada conexión envía código Python (texto UTF-8),
cierra su lado de escritura y recibe una respuesta JSON:
  {"ok": bool, "output": str, "result": str | None, "error": str | None}

El código se ejecuta en el hilo principal de Blender (vía bpy.app.timers),
con un espacio de nombres persistente entre llamadas. Si el código asigna
una variable llamada `result`, su repr() se devuelve en la respuesta.
"""

bl_info = {
    "name": "Claude Bridge",
    "author": "rapanuti + Claude",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Vista 3D > Barra lateral (N) > Claude",
    "description": "Servidor local para que Claude controle Blender con Python",
    "category": "Development",
}

import contextlib
import io
import json
import queue
import socket
import threading
import traceback

import bpy

HOST = "127.0.0.1"
PORT = 9876
TIMEOUT = 600  # segundos que el servidor espera a que termine un comando

_requests = queue.Queue()
_namespace = {}
_server_socket = None
_server_thread = None


def _execute(code):
    buf = io.StringIO()
    _namespace["bpy"] = bpy
    _namespace.pop("result", None)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(code, "<claude>", "exec"), _namespace)
        result = _namespace.get("result")
        return {
            "ok": True,
            "output": buf.getvalue(),
            "result": None if result is None else repr(result),
            "error": None,
        }
    except Exception:
        return {"ok": False, "output": buf.getvalue(), "result": None, "error": traceback.format_exc()}


def _process_queue():
    while True:
        try:
            code, reply = _requests.get_nowait()
        except queue.Empty:
            break
        reply.put(_execute(code))
    return 0.05


def _recv_all(conn):
    chunks = []
    while True:
        data = conn.recv(65536)
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks).decode("utf-8")


def _handle(conn):
    with conn:
        try:
            code = _recv_all(conn)
            reply = queue.Queue(maxsize=1)
            _requests.put((code, reply))
            try:
                response = reply.get(timeout=TIMEOUT)
            except queue.Empty:
                response = {"ok": False, "output": "", "result": None, "error": "Tiempo de espera agotado"}
        except Exception:
            response = {"ok": False, "output": "", "result": None, "error": traceback.format_exc()}
        conn.sendall(json.dumps(response).encode("utf-8"))


def _serve(sock):
    while True:
        try:
            conn, _ = sock.accept()
        except OSError:
            break  # socket cerrado al detener el servidor
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()


def is_running():
    return _server_socket is not None


def start_server():
    global _server_socket, _server_thread
    if is_running():
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(5)
    _server_socket = sock
    _server_thread = threading.Thread(target=_serve, args=(sock,), daemon=True)
    _server_thread.start()
    if not bpy.app.timers.is_registered(_process_queue):
        bpy.app.timers.register(_process_queue, persistent=True)
    print(f"[Claude Bridge] Escuchando en {HOST}:{PORT}")


def stop_server():
    global _server_socket, _server_thread
    if _server_socket is not None:
        _server_socket.close()
        _server_socket = None
        _server_thread = None
    if bpy.app.timers.is_registered(_process_queue):
        bpy.app.timers.unregister(_process_queue)
    print("[Claude Bridge] Detenido")


class CLAUDE_OT_toggle_server(bpy.types.Operator):
    bl_idname = "claude.toggle_server"
    bl_label = "Iniciar/Detener Claude Bridge"

    def execute(self, context):
        try:
            stop_server() if is_running() else start_server()
        except OSError as e:
            self.report({"ERROR"}, f"No se pudo abrir el puerto {PORT}: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class CLAUDE_PT_panel(bpy.types.Panel):
    bl_label = "Claude Bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Claude"

    def draw(self, context):
        layout = self.layout
        if is_running():
            layout.label(text=f"Conectado en puerto {PORT}", icon="LINKED")
            layout.operator("claude.toggle_server", text="Detener", icon="PAUSE")
        else:
            layout.label(text="Detenido", icon="UNLINKED")
            layout.operator("claude.toggle_server", text="Iniciar", icon="PLAY")


_classes = (CLAUDE_OT_toggle_server, CLAUDE_PT_panel)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    if not bpy.app.background:
        try:
            start_server()
        except OSError as e:
            print(f"[Claude Bridge] No se pudo iniciar: {e}")


def unregister():
    stop_server()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
