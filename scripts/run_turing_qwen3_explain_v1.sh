#!/bin/bash
#SBATCH --job-name=qwen3-4b-explain-v1
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
OUTPUT_DIR="${OUTPUT_DIR:-$TURING_SCRATCH/outputs/explain-v1}"
EXPLAIN_INPUT="${EXPLAIN_INPUT:-$PROJECT_DIR/artifacts/deepseek-v4-flash/explain/v1-111/results.json}"
EXPLAIN_OUTPUT_FILE="${EXPLAIN_OUTPUT_FILE:-$OUTPUT_DIR/qwen3-4b-explain-v1-111-valid-medium-results.json}"
EXPLAIN_REPORT_FILE="${EXPLAIN_REPORT_FILE:-$OUTPUT_DIR/qwen3-4b-explain-v1-111-valid-medium-report.txt}"
STUDENT_EXPLAIN_PROMPT="${STUDENT_EXPLAIN_PROMPT:-$PROJECT_DIR/data/prompts/explain/student_explain.md}"

if [[ "$PROJECT_DIR" != "$HOME/anlp-project" ]]; then
    echo "unexpected project directory: $PROJECT_DIR" >&2
    exit 20
fi
if [[ "$TURING_SCRATCH" != /scratch/mukund.hebbar/qwen3-4b* ]]; then
    echo "scratch path is outside the permitted personal tree: $TURING_SCRATCH" >&2
    exit 21
fi
mkdir -p "$OUTPUT_DIR"

EVAL_MODE=explain-v1 OUTPUT_DIR="$OUTPUT_DIR" \
EXPLAIN_INPUT="$EXPLAIN_INPUT" \
EXPLAIN_OUTPUT_FILE="$EXPLAIN_OUTPUT_FILE" \
EXPLAIN_REPORT_FILE="$EXPLAIN_REPORT_FILE" \
STUDENT_EXPLAIN_PROMPT="$STUDENT_EXPLAIN_PROMPT" \
    "$PROJECT_DIR/scripts/run_turing_qwen3_eval.sh"
