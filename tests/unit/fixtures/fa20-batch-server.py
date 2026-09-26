"""FA20's batch-lane fixture server (no network).

Replays the two exchanges FA2 recorded on the batch lane
(docs/research-2026-09-11-batch-lane.md:84-131) against loopback: a
``POST /api/beta/batches`` answered ``202`` with the validating object, and
``GET /api/beta/batches/<id>`` answered ``in_progress`` on the first call and
the completed object on the second. Special ids steer the cases:

  batch-1789094338-KsxdGYx0U4WjU5j0W5La  -> in_progress, then completed
  batch-fail     -> status "failed" (terminal, no results)
  batch-stall    -> always "in_progress" (never terminal)
  batch-5xx      -> 503 on the first GET, then completed (the retry case)
  batch-nonesuch -> 404 with a JSON error body
  batch-429      -> completed with one result whose response.status_code is 429
  batch-traverse -> completed with one result whose custom_id is "../../escaped"
  batch-absolute -> completed with one result whose custom_id is "/abs/escaped"
  batch-newline  -> completed with one result whose custom_id is "abc\\n" (a
                    trailing newline embedded in the id, FA20c's fullmatch case)
  batch-hidden   -> completed with one result whose custom_id is ".hidden"
                    (contained, off-alphabet, FA20c's regex-discrimination case)

The next POST's id is read from the ``FA20_NEXT_ID`` environment variable when
present: if it names a file, its first line (stripped) is the id; otherwise the
value is the id itself (FA21's cases). ``FA20_SUBMIT_STATUS`` overrides the
POST status (default 202; the 400 case). Every received request (method, path,
lower-cased headers, body text) is appended to the path given by ``--log``
(or ``FA20_REQ_LOG``). Listens on 127.0.0.1 at a free port and prints
``PORT=<n>`` on stdout once bound.
"""

import argparse
import http.server
import json
import os
import threading

DEFAULT_ID = "batch-1789094338-KsxdGYx0U4WjU5j0W5La"
RECORDED_MODEL = "anthropic/claude-fable-5.1-20260831"
RESULT_MODEL = "anthropic/claude-fable-5.1:batch"


def _validating(batch_id, model):
    return {
        "id": batch_id,
        "object": "batch",
        "endpoint": "/v1/chat/completions",
        "model": model,
        "completion_window": "24h",
        "status": "validating",
        "created_at": 1789094338,
        "finalized_at": None,
        "request_counts": {"total": 1, "completed": 0, "failed": 0},
        "usage": None,
        "results": None,
        "error": None,
    }


def _in_progress(batch_id):
    body = _validating(batch_id, RECORDED_MODEL)
    body["status"] = "in_progress"
    return body


def _completed(batch_id):
    return {
        "id": batch_id,
        "object": "batch",
        "endpoint": "/v1/chat/completions",
        "model": RECORDED_MODEL,
        "completion_window": "24h",
        "status": "completed",
        "created_at": 1789094338,
        "finalized_at": 1789094597,
        "request_counts": {"total": 1, "completed": 1, "failed": 0},
        "usage": {
            "prompt_tokens": 13,
            "completion_tokens": 13,
            "total_tokens": 26,
            "cost": 0.00039,
            "is_byok": False,
        },
        "error": None,
        "results": [
            {
                "id": "msg_011Cevss1fFYOZzEPdGsWZyYT",
                "custom_id": "fa2-probe-1",
                "response": {
                    "status_code": 200,
                    "request_id": None,
                    "body": {
                        "model": RESULT_MODEL,
                        "id": "gen-batch-1789094338-812ddd369b57b85dbb12",
                        "object": "chat.completion",
                        "service_tier": "batch",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "Hello, how can I help you today?",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "provider": "Anthropic",
                    },
                },
                "error": None,
            }
        ],
    }


def _failed(batch_id):
    body = _validating(batch_id, RECORDED_MODEL)
    body["status"] = "failed"
    body["finalized_at"] = 1789094597
    body["request_counts"] = {"total": 1, "completed": 0, "failed": 1}
    body["usage"] = None
    body["results"] = None
    body["error"] = {"message": "batch failed"}
    return body


def _resulted(batch_id, custom_id):
    body = _completed(batch_id)
    body["results"] = [
        {
            "id": "msg_fix_round",
            "custom_id": custom_id,
            "response": {
                "status_code": 200,
                "request_id": None,
                "body": {"custom_id": custom_id},
            },
            "error": None,
        }
    ]
    return body


def _rate_limited(batch_id):
    body = _validating(batch_id, RECORDED_MODEL)
    body["status"] = "completed"
    body["finalized_at"] = 1789094597
    body["request_counts"] = {"total": 1, "completed": 0, "failed": 1}
    body["usage"] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost": 0.0,
        "is_byok": False,
    }
    body["error"] = None
    body["results"] = [
        {
            "id": "msg_err_1",
            "custom_id": "rate-limited-probe",
            "response": {
                "status_code": 429,
                "request_id": None,
                "body": {"error": {"message": "rate limited"}},
            },
            "error": None,
        }
    ]
    return body


def _control(name, default):
    """Read a per-request control from the file named by env var `name`.

    The value is a FILE PATH, re-read fresh on each request so a test can write
    it between requests while the server stays up. A missing or empty file
    means no override: return `default`.
    """
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    if not os.path.isfile(value):
        return default
    with open(value, encoding="utf-8") as f:
        content = f.read().strip()
    return content if content != "" else default


def _append_log(log_path, command, path, headers, body_text):
    if not log_path:
        return
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{command} {path}\n")
        f.writelines(f"{name.lower()}: {value}\n" for name, value in headers.items())
        f.write(f"{body_text}\n")


def _make_handler(state, log_path):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def _reply(self, code, obj):
            body = b"" if obj is None else json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _batch_id(self):
            return self.path.rstrip("/").rsplit("/", 1)[-1]

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", "replace")
            _append_log(log_path, self.command, self.path, dict(self.headers), raw)
            status = int(_control("FA20_SUBMIT_STATUS", "202"))
            if status != 202:
                self._reply(status, {"error": {"message": "bad request"}})
                return
            try:
                request_obj = json.loads(raw) if raw else {}
            except ValueError:
                request_obj = {}
            model = request_obj.get("model", RECORDED_MODEL)
            self._reply(202, _validating(_control("FA20_NEXT_ID", DEFAULT_ID), model))

        def do_GET(self):
            _append_log(log_path, self.command, self.path, dict(self.headers), "")
            batch_id = self._batch_id()
            if batch_id == "batch-nonesuch":
                self._reply(404, {"error": {"message": f"no such batch {batch_id}"}})
                return
            if batch_id == "batch-fail":
                self._reply(200, _failed(batch_id))
                return
            if batch_id == "batch-stall":
                self._reply(200, _in_progress(batch_id))
                return
            if batch_id == "batch-429":
                self._reply(200, _rate_limited(batch_id))
                return
            if batch_id == "batch-traverse":
                self._reply(200, _resulted(batch_id, "../../escaped"))
                return
            if batch_id == "batch-absolute":
                self._reply(200, _resulted(batch_id, "/abs/escaped"))
                return
            if batch_id == "batch-newline":
                self._reply(200, _resulted(batch_id, "abc\n"))
                return
            if batch_id == "batch-hidden":
                self._reply(200, _resulted(batch_id, ".hidden"))
                return
            if batch_id == "batch-5xx":
                with state.lock:
                    hits = state.hits.get(batch_id, 0) + 1
                    state.hits[batch_id] = hits
                if hits == 1:
                    self._reply(503, {"error": {"message": "temporarily unavailable"}})
                else:
                    self._reply(200, _completed(batch_id))
                return
            with state.lock:
                hits = state.hits.get(batch_id, 0) + 1
                state.hits[batch_id] = hits
            if hits == 1:
                self._reply(200, _in_progress(batch_id))
            else:
                self._reply(200, _completed(batch_id))

    return Handler


class _State:
    def __init__(self):
        self.hits = {}
        self.lock = threading.Lock()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--log", default="", help="request-log path (FA20_REQ_LOG overrides)"
    )
    args = parser.parse_args(argv)
    log_path = os.environ.get("FA20_REQ_LOG") or args.log
    state = _State()
    httpd = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), _make_handler(state, log_path)
    )
    print(f"PORT={httpd.server_address[1]}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
