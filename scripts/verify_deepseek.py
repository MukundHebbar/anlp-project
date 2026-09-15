#!/usr/bin/env python3
"""Verify DeepSeek SOLVE outputs against dataset answers."""

from anlp_project.verify_solutions import parse_args, render_report, verify_manifest


if __name__ == "__main__":
    args = parse_args()
    result = verify_manifest(args.manifest, args.solutions, args.output)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result), encoding="utf-8")
    print(f"wrote verification output to {args.output}")
    print(f"wrote verification report to {args.report}")
