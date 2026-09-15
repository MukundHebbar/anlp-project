#!/usr/bin/env python3
"""Build a one-record EXPLAIN smoke manifest."""

from anlp_project.build_explain_smoke import build_smoke, parse_args


if __name__ == "__main__":
    args = parse_args()
    build_smoke(args.source, args.output)
