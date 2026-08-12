#!/usr/bin/env python3
"""Local server for the site, with cache headers that tell the truth.

`python3 -m http.server` sends no Cache-Control at all. Browsers fall back to
a heuristic in that case — roughly a tenth of the file's age — and quietly
reuse index.html without asking the server. That breaks the whole versioning
scheme, because the ?v= cache busters live *inside* index.html: a stale
document keeps pointing at the stale stylesheet, and the page looks unchanged
no matter what was edited. A hard reload fixes it for one load and then it
drifts again.

So: the document is always revalidated, and everything it references is free
to be cached hard, because its URL changes whenever its contents do.

    python3 serve.py [port]
"""
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4560


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = self.path.split("?", 1)[0]
        if path.endswith((".html", "/")):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        else:
            self.send_header("Cache-Control", "public, max-age=31536000")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "404" in (fmt % args):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    handler = partial(Handler, directory=str(Path(__file__).parent))
    with ThreadingHTTPServer(("", PORT), handler) as httpd:
        print(f"http://localhost:{PORT}  (html revalidated, assets cached)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
