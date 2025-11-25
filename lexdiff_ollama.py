"""Run lexdiff and request an Ollama-based LLM review."""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from lexdiff import DependencyError, compute_diff
from lexdiff.ollama import DEFAULT_HOST, OllamaUnavailable, ensure_ollama_cli, request_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare DOCX files and request an Ollama review.")
    parser.add_argument("source", help="Original DOCX document")
    parser.add_argument("target", help="Revised DOCX document")
    parser.add_argument("--ignore", default="", help="Comma separated list of ignore options (punct, space)")
    parser.add_argument("--threshold", type=float, default=0.8, help="Similarity threshold (0-1) for replacements")
    parser.add_argument("--model", default="llama3", help="Ollama model name (default: llama3)")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Ollama host URL (default: http://localhost:11434)")
    parser.add_argument("--limit", type=int, default=30, help="Maximum number of changes to include in the prompt")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    args.ignore_tokens = [token.strip() for token in args.ignore.split(",") if token.strip()]
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")
    if args.limit <= 0:
        parser.error("--limit must be a positive integer")

    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        ensure_ollama_cli()
        diff = compute_diff(
            source=args.source,
            target=args.target,
            ignore_tokens=args.ignore_tokens,
            threshold=args.threshold,
        )
        review = request_review(
            diff,
            source_name=args.source,
            target_name=args.target,
            model=args.model,
            host=args.host,
            change_limit=args.limit,
        )
    except DependencyError as exc:
        print(exc, file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    except OllamaUnavailable as exc:
        print(exc, file=sys.stderr)
        return 3

    print("\n=== Ollama 리뷰 ===\n")
    print(review)

    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    raise SystemExit(main())
