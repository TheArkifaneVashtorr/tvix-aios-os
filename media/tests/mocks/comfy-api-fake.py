"""A stdlib HTTP fake of ComfyUI's API for the comfy-worlds queue tests.

Runs the smallest surface `pkgs/comfy-worlds/queue.py` drives:

- `POST /prompt` — records the body and answers `{"prompt_id": "<id>"}`.
- `GET /history/<id>` — `{}` (absent) until `tick()` or `fail()` records a
  result for that id.
- `GET /system_stats` — a fixed JSON answer so a client can health-check.

`FakeComfy(port=0)` binds an ephemeral loopback port, is `.start()`-ed in a
thread, and answers on `.url`. `tick(filename)` makes every submitted prompt
id report one done image with that filename; `fail(prompt_id, msg)` makes one
id report `status.status_str == "error"`. `.prompts` holds the parsed
`POST /prompt` bodies in arrival order, for asserting the seed the queue
pinned. Importable (the queue tests start it in a thread) and runnable
(`python tests/mocks/comfy-api-fake.py --port 8188`).
"""

import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeComfy:
    """An in-process ComfyUI API fake on `127.0.0.1:<port>`."""

    def __init__(self, port=0):
        self._tick_filename = None
        self._failures = {}
        self.prompts = []
        handler = _make_handler(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self._thread = None

    def start(self):
        """Serve in a daemon thread; `.url` is valid immediately after."""
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def tick(self, filename):
        """Report every submitted prompt id as done with this filename."""
        self._tick_filename = filename

    def fail(self, prompt_id, msg):
        """Report one prompt id as `status_str == "error"` with `msg`."""
        self._failures[prompt_id] = msg

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def _history(self, pid):
        if pid in self._failures:
            return {
                pid: {
                    "status": {
                        "status_str": "error",
                        "messages": [[self._failures[pid]]],
                    }
                }
            }
        if self._tick_filename is not None:
            return {
                pid: {
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": self._tick_filename,
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    },
                    "status": {"status_str": "success"},
                }
            }
        return {}


def _make_handler(fake):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence stderr access-log spam
            pass

        def _json(self, code, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            fake.prompts.append(json.loads(body))
            self._json(200, {"prompt_id": str(uuid.uuid4())})

        def do_GET(self):
            if self.path == "/system_stats":
                self._json(200, {"system": {"comfyui_version": "fake"}})
                return
            prefix = "/history/"
            if self.path.startswith(prefix):
                self._json(200, fake._history(self.path[len(prefix) :]))
                return
            self._json(404, {"error": "not found"})

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(prog="comfy-api-fake")
    parser.add_argument("--port", type=int, default=8188)
    args = parser.parse_args(argv)
    fake = FakeComfy(args.port)
    fake.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        fake.stop()


if __name__ == "__main__":
    main()
