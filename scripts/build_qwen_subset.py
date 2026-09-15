#!/usr/bin/env python3
"""Build the verified-correct Qwen SOLVE subset."""

from anlp_project.build_qwen_correct_subset import build_subset, parse_args


if __name__ == "__main__":
    args = parse_args()
    build_subset(args.input, args.output, args.smoke_output)
