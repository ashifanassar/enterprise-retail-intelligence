import json
import subprocess
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

API_BASE = "https://retail-ai-api-1039944541778.us-central1.run.app"
API_KEY = "retail-ai-mvp-secret-2026"


def identity_token():
    return subprocess.check_output(
        ["gcloud", "auth", "print-identity-token"],
        text=True,
    ).strip()


class Handler(SimpleHTTPRequestHandler):
    def _proxy(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))

        req = urllib.request.Request(
            API_BASE + self.path,
            data=body if body else None,
            method=self.command,
            headers={
                "Authorization": f"Bearer {identity_token()}",
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                data = res.read()
                self.send_response(res.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(e.read())

    def do_GET(self):
        if self.path == "/health":
            return self._proxy()
        return super().do_GET()

    def do_POST(self):
        if self.path in ["/search", "/chat"]:
            return self._proxy()
        self.send_error(404)


if __name__ == "__main__":
    print("Demo running on http://localhost:8080/retail-ai-demo.html")
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
