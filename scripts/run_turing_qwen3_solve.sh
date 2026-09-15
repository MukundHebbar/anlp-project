#!/bin/bash
#SBATCH --job-name=qwen3-4b-solve-146
#SBATCH --account=priyesh.shukla
#SBATCH --partition=u22
#SBATCH --constraint=l40s
#SBATCH --nodelist=node11
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --output=logs/slurm-%x-%j.out
#SBATCH --error=logs/slurm-%x-%j.err

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/anlp-project}"
TURING_SCRATCH="${TURING_SCRATCH:-/scratch/mukund.hebbar/qwen3-4b}"
OUTPUT_DIR="${OUTPUT_DIR:-$TURING_SCRATCH/outputs/solve-146}"
SOLVE_INPUT="${SOLVE_INPUT:-$PROJECT_DIR/data/manifests/deepmath/deepmath-pilot-146.json}"
SOLVE_OUTPUT_FILE="${SOLVE_OUTPUT_FILE:-$OUTPUT_DIR/qwen3-4b-solve-146-results.json}"
SOLVE_REPORT_FILE="${SOLVE_REPORT_FILE:-$OUTPUT_DIR/qwen3-4b-solve-146-report.txt}"

if [[ "$PROJECT_DIR" != "$HOME/anlp-project" ]]; then
    echo "unexpected project directory: $PROJECT_DIR" >&2
    exit 20
fi
if [[ "$TURING_SCRATCH" != /scratch/mukund.hebbar/qwen3-4b* ]]; then
    echo "scratch path is outside the permitted personal tree: $TURING_SCRATCH" >&2
    exit 21
fi
if [[ "$SOLVE_INPUT" != "$PROJECT_DIR"/* ]]; then
    echo "SOLVE_INPUT must remain inside the synced project tree: $SOLVE_INPUT" >&2
    exit 22
fi
mkdir -p "$OUTPUT_DIR"

EVAL_MODE=solve-only \
OUTPUT_DIR="$OUTPUT_DIR" \
SOLVE_INPUT="$SOLVE_INPUT" \
SOLVE_OUTPUT_FILE="$SOLVE_OUTPUT_FILE" \
SOLVE_REPORT_FILE="$SOLVE_REPORT_FILE" \
    bash "$PROJECT_DIR/scripts/run_turing_qwen3_eval.sh"
