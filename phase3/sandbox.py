"""Run model-written Python programs for evidence.py (program checks and program-of-thought).

Each program runs in its own temporary directory with `python -I`, an empty environment, CPU/memory/file-size limits and
a 10 s wall clock, inside unprivileged user + mount + network namespaces (`unshare -rmn`): no network, and tmpfs mounts
hide the repository, the run outputs, ~/.ssh, ~/.cache, ~/.config and the model cache. The regex denylist is only a
first filter (status "blocked"); the namespaces are the isolation boundary. Missing `unshare` is an error, not a
fallback.
Results are added in place to each completion: {code, status, last_line}.
status: ok | no_code | blocked | timeout | error | no_output
"""

import os
import re
import resource
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

_CODE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
_BLOCK = re.compile(r"\b(import\s+(os|subprocess|shutil|socket|requests|urllib|pathlib|ctypes|multiprocessing|"
                    r"threading|signal|pickle|glob|tempfile|http)\b|from\s+(os|subprocess|shutil|socket|requests|"
                    r"urllib|pathlib|ctypes|multiprocessing|threading|signal|pickle|glob|tempfile|http)\b|__import__|"
                    r"\bopen\s*\(|\beval\s*\(|\bexec\s*\(|\bcompile\s*\(|input\s*\(|"
                    r"\b(os|subprocess|shutil|socket|pathlib|ctypes)\s*[,.]|,\s*(os|subprocess|shutil|socket)\b)")
TIMEOUT = 10
HOME = os.path.expanduser("~")
HIDE = [f"{HOME}/anlp-project", f"{HOME}/.ssh", f"{HOME}/.cache", f"{HOME}/.config",
        os.environ.get("HF_HOME", "/nonexistent")]
_JAIL = ("for p in " + " ".join(f"'{p}'" for p in HIDE) + "; do [ -d \"$p\" ] && mount -t tmpfs none \"$p\"; done; "
         'exec "$0" -I prog.py')


def extract(text):
    blocks = _CODE.findall(text or "")
    return blocks[-1] if blocks else None


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT, TIMEOUT))
    resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
    os.setsid()


def run(code):
    if code is None:
        return "no_code", None
    if _BLOCK.search(code):
        return "blocked", None
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.py")
        with open(path, "w") as fh:
            fh.write(code)
        try:
            p = subprocess.run(["unshare", "-rmn", "sh", "-c", _JAIL, sys.executable], cwd=d, capture_output=True, text=True, timeout=TIMEOUT,
                               env={"PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"},
                               preexec_fn=_limits, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return "timeout", None
    lines = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
    if p.returncode != 0:
        return "error", lines[-1][:300] if lines else None
    if not lines:
        return "no_output", None
    return "ok", lines[-1][:300]


def execute_all(records, workers=8):
    comps = [c for r in records for c in r["outputs"]]
    codes = [extract(c["text"]) for c in comps]
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(run, codes))
    for c, code, (status, last) in zip(comps, codes, results, strict=True):
        c.update(code=code, status=status, last_line=last)
