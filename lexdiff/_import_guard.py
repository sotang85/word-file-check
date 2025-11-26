"""Utility to detect merge-conflict markers before importing the package."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional


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


def _find_conflict(root: Path, *, tokens: Iterable[str]) -> Optional[Path]:
    """Return the first Python file containing merge-conflict markers, if any."""

    for path in root.rglob("*.py"):
        try:
            contents = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(token in contents for token in tokens):
            return path
    return None


def ensure_tree_clean(root: Path, *, tokens: Iterable[str] = ("<<<<<<<", "=======", ">>>>>>>")) -> None:
    """Scan an entire tree for conflict markers before importing anything heavy."""

    conflict = _find_conflict(root, tokens=tokens)
    if conflict is None:
        return

    try:
        relative = conflict.relative_to(root)
    except ValueError:
        relative = conflict

    raise SystemExit(
        "lexdiff 소스에 병합 충돌 표식(======= 등)이 남아 있어 실행할 수 없습니다.\n"
        f"문제가 된 파일: {relative}\n"
        "레포지토리를 깨끗한 상태로 다시 받거나 충돌을 해결한 뒤 다시 실행해 주세요."
    )
