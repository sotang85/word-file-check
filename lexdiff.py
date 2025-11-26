#!/usr/bin/env python3
"""Entry point for the lexdiff CLI."""
from __future__ import annotations

from pathlib import Path

from lexdiff._import_guard import ensure_tree_clean

ensure_tree_clean(Path(__file__).resolve().parent)

try:
    from lexdiff.cli import main
except SyntaxError as exc:  # pragma: no cover - import-time guard
    raise SystemExit(
        "lexdiff 소스에 병합 충돌 표식(======= 등)이 남아 있어 실행할 수 없습니다.\n"
        "레포지토리를 깨끗한 상태로 다시 받아 CLI를 실행해 주세요."
    ) from exc


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    raise SystemExit(main())
