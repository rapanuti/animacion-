#!/usr/bin/env python3
"""Envía código Python al Blender que está corriendo con el add-on Claude Bridge.

Uso:
  python3 blender_bridge/send.py archivo.py
  python3 blender_bridge/send.py -c "print(bpy.app.version_string)"
  echo "..." | python3 blender_bridge/send.py
"""

import argparse
import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 9876


def send(code, timeout=600):
    with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
        sock.sendall(code.encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            data = sock.recv(65536)
            if not data:
                break
            chunks.append(data)
    return json.loads(b"".join(chunks).decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", help="archivo .py a ejecutar (por defecto, stdin)")
    parser.add_argument("-c", "--code", help="código a ejecutar directamente")
    args = parser.parse_args()

    if args.code is not None:
        code = args.code
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            code = f.read()
    else:
        code = sys.stdin.read()

    try:
        response = send(code)
    except ConnectionRefusedError:
        sys.exit(f"No hay conexión con Blender en {HOST}:{PORT}. ¿Está abierto con el add-on Claude Bridge activo?")

    if response["output"]:
        print(response["output"], end="")
    if response["result"] is not None:
        print(f"result = {response['result']}")
    if not response["ok"]:
        print(response["error"], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
