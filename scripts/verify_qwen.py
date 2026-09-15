#!/usr/bin/env python3
"""Verify Qwen outputs locally with the deterministic verifier."""

from anlp_project.verify_qwen_results import parse_args, render_report, verify_qwen_results


if __name__ == "__main__":
    args = parse_args()
    result = verify_qwen_results(args.input, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result), encoding="utf-8")
    print(f"wrote local Qwen verification to {args.output}")
    print(f"wrote report to {args.report}")
