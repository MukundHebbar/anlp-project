#!/bin/bash
# Build a complete, binary-only CPython 3.12 wheelhouse for Turing.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${DEST_DIR:-$ROOT_DIR/wheelhouse/qwen3-4b-py312-cu126-full}"
INPUT_FILE="${INPUT_FILE:-$ROOT_DIR/requirements-turing-qwen3.in}"
UV_BIN="${UV_BIN:-$(command -v uv || true)}"
BUILD_TMP_ROOT="${BUILD_TMP_ROOT:-$ROOT_DIR/.wheelhouse-build-tmp}"
PYTHON_VERSION="3.12"
PYTHON_PLATFORM="x86_64-manylinux_2_28"
TORCH_INDEX="https://download.pytorch.org/whl/cu126"

if [[ "$(uname -m)" != "x86_64" ]]; then
    echo "this wheelhouse must be built on an x86_64 workstation" >&2
    exit 2
fi

if [[ -z "$UV_BIN" ]]; then
    echo "uv is required locally to resolve the pinned wheelhouse" >&2
    exit 2
fi
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "requirements input is missing: $INPUT_FILE" >&2
    exit 2
fi

mkdir -p "$BUILD_TMP_ROOT"
STAGING_DIR="$(mktemp -d "$BUILD_TMP_ROOT/staging.XXXXXX")"
cleanup() {
    rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

mkdir -p "$STAGING_DIR/tmp"
export TMPDIR="$STAGING_DIR/tmp"

LOCK_FILE="$STAGING_DIR/requirements.lock.txt"
WHEELS_DIR="$STAGING_DIR/wheels"
SEED_DIRS=("$ROOT_DIR/wheelhouse/qwen3-4b")
if [[ "$DEST_DIR" != "$ROOT_DIR/wheelhouse/qwen3-4b" && -d "$ROOT_DIR/wheelhouse/qwen3-4b-py312-cu126-full" ]]; then
    SEED_DIRS+=("$ROOT_DIR/wheelhouse/qwen3-4b-py312-cu126-full")
fi
mkdir -p "$WHEELS_DIR"

PIP_FIND_LINKS_ARGS=()
for seed_dir in "${SEED_DIRS[@]}"; do
    if [[ ! -d "$seed_dir" ]]; then
        continue
    fi
    PIP_FIND_LINKS_ARGS+=(--find-links "$seed_dir")
    # Put already-verified large artifacts directly in the staging directory so
    # pip does not prefer a same-version remote candidate over the local file.
    find "$seed_dir" -maxdepth 1 -type f -name '*.whl' -exec cp -n {} "$WHEELS_DIR/" \;
done

"$UV_BIN" pip compile "$INPUT_FILE" \
    --python-version "$PYTHON_VERSION" \
    --python-platform "$PYTHON_PLATFORM" \
    --only-binary=:all: \
    --torch-backend=cu126 \
    --extra-index-url "$TORCH_INDEX" \
    --generate-hashes \
    --no-header \
    --no-annotate \
    --output-file "$LOCK_FILE" \
    >/dev/null

python3 -m pip download \
    --require-hashes \
    --no-deps \
    --dest "$WHEELS_DIR" \
    "${PIP_FIND_LINKS_ARGS[@]}" \
    --only-binary=:all: \
    --python-version "$PYTHON_VERSION" \
    --implementation cp \
    --abi cp312 \
    --extra-index-url "$TORCH_INDEX" \
    --progress-bar on \
    --requirement "$LOCK_FILE"

if ! find "$WHEELS_DIR" -maxdepth 1 -type f -name '*.whl' -print -quit | grep -q .; then
    echo "wheelhouse resolution produced no wheels" >&2
    exit 3
fi

RELEASE_DIR="$STAGING_DIR/release"
mkdir -p "$RELEASE_DIR"
cp "$LOCK_FILE" "$RELEASE_DIR/requirements.lock.txt"
(
    cd "$WHEELS_DIR"
    : > "$RELEASE_DIR/wheelhouse.sha256"
    for wheel in *.whl; do
        digest="$(sha256sum "$wheel" | awk '{print $1}')"
        if grep -Fq -- "sha256:$digest" "$LOCK_FILE"; then
            cp "$wheel" "$RELEASE_DIR/$wheel"
            printf '%s  %s\n' "$digest" "$wheel" >> "$RELEASE_DIR/wheelhouse.sha256"
        fi
    done
)
sha256sum "$RELEASE_DIR/requirements.lock.txt" | sed "s#${STAGING_DIR}/release/##" > "$RELEASE_DIR/requirements.lock.sha256"

if [[ -e "$DEST_DIR" && "${ALLOW_REPLACE:-0}" != "1" ]]; then
    echo "destination exists; set ALLOW_REPLACE=1 to replace only this exact directory: $DEST_DIR" >&2
    exit 4
fi
if [[ -e "$DEST_DIR" ]]; then
    rm -rf "$DEST_DIR"
fi
mkdir -p "$(dirname "$DEST_DIR")"
mv "$RELEASE_DIR" "$DEST_DIR"

count="$(find "$DEST_DIR" -maxdepth 1 -type f -name '*.whl' | wc -l)"
bytes="$(find "$DEST_DIR" -maxdepth 1 -type f -name '*.whl' -printf '%s\n' | awk '{s += $1} END {print s + 0}')"
printf 'wheel_count=%s\nwheel_bytes=%s\nwheelhouse=%s\nlockfile=%s\n' \
    "$count" "$bytes" "$DEST_DIR" "$DEST_DIR/requirements.lock.txt"
