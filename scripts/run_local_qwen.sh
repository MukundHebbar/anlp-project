#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
server_bin="${LLAMA_SERVER_BIN:-$project_dir/local/runtime/llama.cpp/build/bin/llama-server}"
model_file="${QWEN_GGUF:-$project_dir/local/models/Qwen3-4B-Q4_K_M.gguf}"
pid_file="$project_dir/artifacts/reconstruct/qwen-server.pid"
log_file="$project_dir/artifacts/reconstruct/qwen-server.log"
action="${1:-start}"

is_running() {
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

stop_server() {
  if is_running; then
    kill "$(cat "$pid_file")"
    for _ in $(seq 1 30); do
      is_running || break
      sleep 1
    done
  fi
  rm -f "$pid_file"
}

server_args=(
  --model "$model_file"
  --alias Qwen/Qwen3-4B
  --host 127.0.0.1
  --port 8080
  --ctx-size 24576
  --parallel 1
  --n-gpu-layers 99
  --flash-attn on
  --cache-type-k q8_0
  --cache-type-v q8_0
  --jinja
  --chat-template-kwargs '{"enable_thinking":false}'
  --reasoning off
  --reasoning-budget 0
  --no-webui
)

case "$action" in
  start)
    if is_running; then
      echo "Qwen server is already running with PID $(cat "$pid_file")"
      exit 0
    fi
    [[ -x "$server_bin" ]] || { echo "Missing llama-server: $server_bin" >&2; exit 1; }
    [[ -s "$model_file" ]] || { echo "Missing Qwen GGUF: $model_file" >&2; exit 1; }
    mkdir -p "$(dirname "$pid_file")"
    nohup "$server_bin" "${server_args[@]}" >"$log_file" 2>&1 &
    echo $! >"$pid_file"
    for _ in $(seq 1 180); do
      if curl --silent --fail http://127.0.0.1:8080/health >/dev/null; then
        echo "Qwen server ready with PID $(cat "$pid_file")"
        exit 0
      fi
      if ! is_running; then
        tail -n 80 "$log_file" >&2
        rm -f "$pid_file"
        exit 1
      fi
      sleep 1
    done
    echo "Qwen server did not become healthy; see $log_file" >&2
    exit 1
    ;;
  foreground)
    exec "$server_bin" "${server_args[@]}"
    ;;
  stop)
    stop_server
    echo "Qwen server stopped"
    ;;
  restart)
    stop_server
    exec "$0" start
    ;;
  status)
    if is_running; then
      echo "running PID $(cat "$pid_file")"
      curl --silent --fail http://127.0.0.1:8080/health || true
    else
      echo "stopped"
      exit 1
    fi
    ;;
  *)
    echo "Usage: $0 {start|foreground|stop|restart|status}" >&2
    exit 2
    ;;
esac
