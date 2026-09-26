"""A scripted OpenAI-compatible upstream for dsh tests (no network).

Stands in for openrouter.ai behind ``dsh-openrouter``: every POST to
``/api/v1/chat/completions`` is captured (path, headers, JSON body) into
``--capture`` and answered with the next entry of ``--script`` as a streamed
chat completion. A script entry is either ``{"content": "text"}`` or
``{"tool": "<tool name substring>", "arguments": {...}}``; the tool entry
picks the first tool in the request whose name contains the substring and
emits one tool call for it. ``GET /api/v1/models`` answers a one-model
listing for dsh's discovery probe. Listens on 127.0.0.1 at a free port
and prints ``PORT=<n>`` on stdout once bound.

Proxy for the real thing: the wire shape (SSE chunks, ``[DONE]``) is what
dsh's openai-completions client accepts; it says nothing about OpenRouter's
own behaviour (routing, ZDR, pricing). Gap: real streams may interleave
reasoning deltas and usage differently.
"""

import argparse
import http.server
import json
import sys
import threading


def _sse(obj):
    return b"data: " + json.dumps(obj).encode("utf-8") + b"\n\n"


def _chunk(index, delta, finish=None, usage=None):
    body = {
        "id": f"chatcmpl-fake-{index}",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "fake/model",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    if usage is not None:
        body["usage"] = usage
    return body


def _tool_call(request_body, entry, index):
    tools = request_body.get("tools") or []
    name = None
    for tool in tools:
        candidate = (tool.get("function") or {}).get("name", "")
        if entry["tool"] in candidate:
            name = candidate
            break
    if name is None:
        raise KeyError(f"no tool containing {entry['tool']!r} in request tools")
    return {
        "index": 0,
        "id": f"call_fake_{index}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(entry["arguments"])},
    }


class _State:
    def __init__(self, script, capture_path):
        self.script = script
        self.capture_path = capture_path
        self.requests = []
        self.lock = threading.Lock()

    def record(self, record):
        with self.lock:
            self.requests.append(record)
            with open(self.capture_path, "w", encoding="utf-8") as f:
                json.dump(self.requests, f, indent=1)
            return len(self.requests) - 1


def _make_handler(state):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                body = json.dumps(
                    {
                        "object": "list",
                        "data": [{"id": "fake/model", "object": "model"}],
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode("utf-8")) if raw else None
            except ValueError:
                body = {"_unparsed": raw.decode("utf-8", "replace")}
            index = state.record(
                {
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": body,
                }
            )
            entry = state.script[min(index, len(state.script) - 1)]
            usage = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            if "tool" in entry:
                call = _tool_call(body or {}, entry, index)
                self.wfile.write(
                    _sse(_chunk(index, {"role": "assistant", "tool_calls": [call]}))
                )
                self.wfile.write(_sse(_chunk(index, {}, "tool_calls", usage)))
            else:
                self.wfile.write(
                    _sse(
                        _chunk(
                            index, {"role": "assistant", "content": entry["content"]}
                        )
                    )
                )
                self.wfile.write(_sse(_chunk(index, {}, "stop", usage)))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--script", required=True, help="JSON list of scripted replies")
    parser.add_argument("--capture", required=True, help="where captured requests go")
    args = parser.parse_args(argv)
    with open(args.script, encoding="utf-8") as f:
        script = json.load(f)
    if not isinstance(script, list) or not script:
        print("openai-fake: --script must be a non-empty JSON list", file=sys.stderr)
        return 2
    state = _State(script, args.capture)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    print(f"PORT={httpd.server_address[1]}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
