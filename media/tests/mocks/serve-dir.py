#!/usr/bin/env python3
"""Minimal stdlib HTTP file server for fetch.bats: serves a directory on
127.0.0.1 at a fixed port. Usage: serve-dir.py <port> <dir>.

Loopback-only, single-purpose test double — not a general server. Used
instead of a network dependency so checks.media-fetch-bats stays hermetic
and build-only.
"""

import http.server
import os
import sys


def main(argv):
    port = int(argv[1])
    directory = argv[2]
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.serve_forever()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
