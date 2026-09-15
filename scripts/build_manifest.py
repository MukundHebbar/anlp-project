#!/usr/bin/env python3
"""Build the reproducible DeepMath evaluation manifests."""

from anlp_project.build_eval_manifest import build_manifests, parse_args


if __name__ == "__main__":
    args = parse_args()
    build_manifests(args.dataset, args.pilot, args.output, args.new_output, args.completed_solutions)
