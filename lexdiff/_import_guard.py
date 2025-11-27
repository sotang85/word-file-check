"""Utility to detect merge-conflict markers before importing the package."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional, Sequence


_DEFAULT_PATTERNS: Sequence[re.Pattern[str]] = (
    re.compile(r"^<<<<<<< .+", flags=re.MULTILINE),
    re.compile(r"^=======$", flags=re.MULTILINE),
    re.compile(r"^>>>>>>> .+", flags=re.MULTILINE),
)


def _contains_conflict_markers(text: str, *, patterns: Sequence[re.Pattern[str]] = _DEFAULT_PATTERNS) -> bool:
    """Return True when merge-conflict markers are present in the given text."""

    return any(pattern.search(text) for pattern in patterns)


def ensure_source_clean(source_path: Path, *, patterns: Sequence[re.Pattern[str]] = _DEFAULT_PATTERNS) -> None:
    """Exit early with a friendly message if conflict markers remain."""

    try:
        contents = source_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    if _contains_conflict_markers(contents, patterns=patterns):
        raise SystemExit(
            "lexdiff 소스에 병합 충돌 표식(======= 등)이 남아 있어 실행할 수 없습니다.\n"
            "레포지토리를 깨끗한 상태로 다시 받거나 충돌을 해결한 뒤 다시 실행해 주세요."
        )


def _find_conflict(
    root: Path,
    *,
    patterns: Sequence[re.Pattern[str]],
    ignore: Sequence[Path] | None = None,
    ignore_names: Iterable[str] = (),
) -> Optional[Path]:
    """Return the first Python file containing merge-conflict markers, if any."""

    ignore_set = {(root / p).resolve() for p in ignore or ()}
    ignore_name_set = set(ignore_names)

    for path in root.rglob("*.py"):
        resolved = path.resolve()
        if resolved in ignore_set or path.name in ignore_name_set:
            continue

        try:
            contents = resolved.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if _contains_conflict_markers(contents, patterns=patterns):
            return path
    return None


_DEFAULT_IGNORE = (Path("tests") / "test_import_guard.py",)


def ensure_tree_clean(
    root: Path,
    *,
    patterns: Sequence[re.Pattern[str]] = _DEFAULT_PATTERNS,
    ignore: Sequence[Path] | None = _DEFAULT_IGNORE,
    ignore_names: Iterable[str] = ("test_import_guard.py",),
) -> None:
    """Scan an entire tree for conflict markers before importing anything heavy."""

    conflict = _find_conflict(
        root, patterns=patterns, ignore=ignore, ignore_names=ignore_names
    )
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
