"""Load the import guard without importing the lexdiff package itself."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
_GUARD_PATH = ROOT / "lexdiff" / "_import_guard.py"


def _load_guard() -> Any:
    spec = importlib.util.spec_from_file_location("lexdiff_import_guard", _GUARD_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - corrupt install
        raise SystemExit(
            "lexdiff 실행 전 검사 모듈을 불러올 수 없습니다.\n"
            "레포지토리를 깨끗한 상태로 다시 받거나 손상 여부를 확인해 주세요."
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


_guard = _load_guard()


def ensure_tree_clean(root: Path | None = None) -> None:
    """Run the merge-marker scan against the given root (default: repo root)."""

    _guard.ensure_tree_clean(root or ROOT)


def ensure_source_clean(source_path: Path) -> None:
    """Proxy to the guard's single-file check."""

    _guard.ensure_source_clean(source_path)
