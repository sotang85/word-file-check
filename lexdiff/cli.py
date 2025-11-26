"""Command line interface for the lexdiff diff engine."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from ._import_guard import ensure_tree_clean

ensure_tree_clean(Path(__file__).resolve().parent)


def _import_core():
    try:
        from . import DependencyError, run_diff  # type: ignore
    except SyntaxError as exc:  # pragma: no cover - import-time guard
        raise SystemExit(
            "lexdiff 소스에 병합 충돌 표식(======= 등)이 남아 있어 실행할 수 없습니다.\n"
            "레포지토리를 깨끗한 상태로 다시 받아주세요."
        ) from exc
    return DependencyError, run_diff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare DOCX files at sentence level.")
    parser.add_argument("source", help="Original DOCX document")
    parser.add_argument("target", help="Revised DOCX document")
    parser.add_argument("--out", dest="out_docx", required=True, help="Path to highlighted DOCX output")
    parser.add_argument("--csv", dest="out_csv", required=True, help="Path to CSV diff report")
    parser.add_argument(
        "--ignore",
        default="",
        help="Comma separated list of ignore options (punct, space)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Similarity threshold (0-1) for classifying replacements",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    tokens = [token.strip() for token in args.ignore.split(",") if token.strip()]
    args.ignore_tokens = tokens

    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")

    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    DependencyError, run_diff = _import_core()

    try:
        run_diff(
            source=args.source,
            target=args.target,
            out_docx=args.out_docx,
            out_csv=args.out_csv,
            ignore_tokens=args.ignore_tokens,
            threshold=args.threshold,
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

    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    raise SystemExit(main())
