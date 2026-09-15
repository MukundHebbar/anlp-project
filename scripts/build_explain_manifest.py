#!/usr/bin/env python3
"""Build a DeepSeek EXPLAIN input manifest."""

from anlp_project.build_explain_input import build_input, parse_args


if __name__ == "__main__":
    args = parse_args()
    build_input(args.source, args.output, args.prompt, args.version)
