#!/usr/bin/env python3
"""Local dev static server for the frontend -- identical to `python3 -m http.server`
except it sends Cache-Control: no-store on every response. Plain http.server applies
normal browser heuristic caching, which repeatedly served stale CSS/JS during
development (a z-index fix, an engine-connect.js fix, etc. all silently didn't apply
until a hard refresh) -- not worth re-diagnosing every time. Not meant for production;
the real deploy target is Nginx (see deploy/nginx/grammatizer.conf), which serves
these same static files with real caching."""

import http.server
import sys


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    http.server.test(HandlerClass=NoCacheHandler, port=port)
