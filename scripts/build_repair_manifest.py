#!/usr/bin/env python3
"""Build a repair manifest for missing final answers."""

from anlp_project.build_repair_input import build_repair_input, parse_args


if __name__ == "__main__":
    args = parse_args()
    build_repair_input(args.manifest, args.solutions, args.output)
