"""Control channel for a Jarvislabs GPU container over its HTTPS endpoint (port 6006).

The campus network blocks outbound SSH to the instances, but HTTPS to *.jarvislabs.net works. A startup script runs
``python3 remote_ctl.py serve`` on the container; this module's client talks to it with a shared token.

    JL_CTL_URL=https://<endpoint> JL_CTL_TOKEN=<token> python phase3/remote_ctl.py run "nvidia-smi"
    ... spawn "<cmd>" <log>      start a background job (survives the request)
    ... put <local> <remote>     upload in chunks
    ... get <remote> <local>     download in chunks
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CHUNK = 4 << 20


# ------------------------------------------------------------------ server (runs on the container)

def serve(token: str, port: int = 6006) -> None:
    class H(BaseHTTPRequestHandler):
        def _ok(self) -> bool:
            if self.headers.get("X-Token") != token:
                self.send_error(403)
                return False
            return True

        def _json(self, obj) -> None:
            data = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._ok():
                return
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/ping":
                return self._json({"ok": True})
            if u.path == "/file":
                p, off, n = q["path"][0], int(q.get("offset", ["0"])[0]), int(q.get("length", [str(CHUNK)])[0])
                size = os.path.getsize(p)
                with open(p, "rb") as f:
                    f.seek(off)
                    data = f.read(n)
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Size", str(size))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)

        def do_POST(self):
            if not self._ok():
                return
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if u.path == "/run":
                req = json.loads(body)
                try:
                    r = subprocess.run(["bash", "-lc", req["cmd"]], capture_output=True, text=True,
                                       timeout=req.get("timeout", 600), cwd=req.get("cwd", "/home"))
                    return self._json({"rc": r.returncode, "out": r.stdout[-30000:], "err": r.stderr[-30000:]})
                except subprocess.TimeoutExpired:
                    return self._json({"rc": -9, "out": "", "err": "timeout"})
            if u.path == "/spawn":
                req = json.loads(body)
                log = open(req["log"], "ab")
                p = subprocess.Popen(["bash", "-lc", req["cmd"]], stdout=log, stderr=subprocess.STDOUT,
                                     cwd=req.get("cwd", "/home"), start_new_session=True)
                return self._json({"pid": p.pid})
            if u.path == "/upload":
                path, off = q["path"][0], int(q.get("offset", ["0"])[0])
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "r+b" if off and os.path.exists(path) else "wb") as f:
                    f.seek(off)
                    f.write(body)
                return self._json({"ok": True, "size": os.path.getsize(path)})
            self.send_error(404)

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


# ------------------------------------------------------------------ client (runs locally)

def _req(method: str, path: str, data: bytes | None = None, timeout: int = 900):
    url = os.environ["JL_CTL_URL"].rstrip("/") + path
    r = urllib.request.Request(url, data=data, method=method, headers={"X-Token": os.environ["JL_CTL_TOKEN"]})
    return urllib.request.urlopen(r, timeout=timeout)


def run(cmd: str, timeout: int = 600) -> dict:
    with _req("POST", "/run", json.dumps({"cmd": cmd, "timeout": timeout}).encode(), timeout + 60) as r:
        return json.loads(r.read())


def spawn(cmd: str, log: str) -> dict:
    with _req("POST", "/spawn", json.dumps({"cmd": cmd, "log": log}).encode()) as r:
        return json.loads(r.read())


def put(local: str, remote: str) -> None:
    size = os.path.getsize(local)
    with open(local, "rb") as f:
        off = 0
        while off < size or off == 0:
            data = f.read(CHUNK)
            with _req("POST", f"/upload?path={urllib.parse.quote(remote)}&offset={off}", data) as r:
                json.loads(r.read())
            off += len(data)
            if not data:
                break


def get(remote: str, local: str) -> None:
    off, size = 0, None
    os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
    with open(local, "wb") as f:
        while size is None or off < size:
            with _req("GET", f"/file?path={urllib.parse.quote(remote)}&offset={off}&length={CHUNK}") as r:
                size = int(r.headers["X-Size"])
                data = r.read()
            f.write(data)
            off += len(data)
            if not data:
                break


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "serve":
        serve(os.environ["JL_CTL_TOKEN"])
    elif cmd == "run":
        res = run(args[0], int(args[1]) if len(args) > 1 else 600)
        print(res["out"], end="")
        print(res["err"], end="", file=sys.stderr)
        sys.exit(res["rc"])
    elif cmd == "spawn":
        print(spawn(args[0], args[1]))
    elif cmd == "put":
        put(args[0], args[1])
    elif cmd == "get":
        get(args[0], args[1])
