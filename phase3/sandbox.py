"""Run model-written Python programs for evidence.py (program checks and program-of-thought).

Each program runs in its own temporary directory with `python -I`, an empty environment, CPU/memory/file-size limits and
a 10 s wall clock, inside unprivileged user + mount + network + PID namespaces
(`unshare -rmnpf --mount-proc --kill-child`): no network, a private /proc, and empty tmpfs mounts over all of $HOME, the repository, /scratch, /tmp, /var/tmp, /run,
/var/run, /dev/shm and the model cache (no host files or Unix sockets there). Only the Python install and the venv
(read-only) and the program's own temporary directory are bound back. Python then starts with an empty capability
bounding set and no_new_privs (`setpriv`), so the program cannot unmount or remount anything. The regex denylist is
only a first filter (status "blocked"); the namespaces are the isolation boundary. Missing `unshare`, `setpriv` or
/mnt is an error, not a fallback.
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
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIDE = [os.path.expanduser("~"), ROOT, "/scratch", "/tmp", "/var/tmp", "/run", "/var/run", "/dev/shm",
        os.environ.get("HF_HOME", "/nonexistent")]
KEEP = sorted({os.path.realpath(p) for p in (sys.prefix, sys.base_prefix)})  # read-only, bound back after hiding
# $1 = program dir. Stage the kept dirs on a tmpfs at /mnt, cover every HIDE path with an empty tmpfs, bind the kept
# dirs (read-only) and the program dir back at their own paths, drop the staging mount, then drop every capability.
_JAIL = ("set -e; d=$1; shift; mount -t tmpfs none /mnt; i=0; for k in \"$d\" \"$@\"; do "
         'mkdir /mnt/$i; mount --bind "$k" /mnt/$i; i=$((i+1)); done; '
         "for p in " + " ".join(f"'{p}'" for p in HIDE) + '; do if [ -d "$p" ] && [ ! -L "$p" ]; then '
         'mount -t tmpfs none "$p"; fi; done; '
         'i=0; for k in "$d" "$@"; do mkdir -p "$k"; mount --bind /mnt/$i "$k"; '
         'if [ $i -gt 0 ]; then mount -o remount,bind,ro "$k"; fi; i=$((i+1)); done; '
         'umount -l /mnt; cd "$d"; '
         'exec setpriv --no-new-privs --inh-caps=-all --ambient-caps=-all --bounding-set=-all "$PY" -I prog.py')


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
            p = subprocess.run(["unshare", "-rmnpf", "--mount-proc", "--kill-child", "sh", "-c", _JAIL, "jail", d,
                                *KEEP], cwd=d, capture_output=True, text=True, timeout=TIMEOUT,
                               env={"PATH": "/usr/bin:/bin", "PY": sys.executable, "OMP_NUM_THREADS": "1",
                                    "OPENBLAS_NUM_THREADS": "1"},
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
