"""Utility to detect merge-conflict markers before importing the package."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def ensure_source_clean(source_path: Path, *, tokens: Iterable[str] = ("<<<<<<<", "=======", ">>>>>>>")) -> None:
    """Exit early with a friendly message if conflict markers remain."""

    try:
        contents = source_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    if any(token in contents for token in tokens):
        raise SystemExit(
            "lexdiff 소스에 병합 충돌 표식(======= 등)이 남아 있어 실행할 수 없습니다.\n"
            "레포지토리를 깨끗한 상태로 다시 받거나 충돌을 해결한 뒤 다시 실행해 주세요."
        )
