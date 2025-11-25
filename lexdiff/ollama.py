"""Ollama 기반 LLM 검토 유틸리티."""
from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from typing import Iterable

from . import DiffResult, Operation

DEFAULT_HOST = "http://localhost:11434"


class OllamaUnavailable(RuntimeError):
    """Raised when the Ollama runtime or API cannot be reached."""


def _normalize_host(host: str) -> str:
    return host[:-1] if host.endswith("/") else host


def build_change_summary(operations: Iterable[Operation], limit: int = 30) -> str:
    """Return a condensed, numbered list of changed sentences for prompting."""

    changed = [op for op in operations if op.kind != "equal"]
    if not changed:
        return "변경 사항이 없습니다."

    lines = []
    for idx, op in enumerate(changed[:limit], start=1):
        original = op.original.text if op.original else "-"
        revised = op.revised.text if op.revised else "-"
        lines.append(
            f"{idx}. [{op.kind}] sim={op.similarity:.2f} | A: {original} | B: {revised}"
        )

    remaining = len(changed) - limit
    if remaining > 0:
        lines.append(f"... {remaining}개 변경이 더 있습니다.")

    return "\n".join(lines)


def build_review_prompt(
    diff: DiffResult,
    source_name: str,
    target_name: str,
    *,
    change_limit: int = 30,
) -> str:
    """Compose a Korean review prompt that highlights key changes."""

    summary = build_change_summary(diff.operations, limit=change_limit)
    return (
        "lexdiff로 추출한 문서 변경 사항을 검토해 주세요.\n"
        f"원본 문서: {source_name}\n"
        f"수정 문서: {target_name}\n"
        "문장 단위 변경 리스트를 보고 핵심 변경점과 영향도를 한국어로 요약하세요.\n"
        "숫자나 날짜 변화가 있으면 구체적으로 언급해 주세요.\n\n"
        "[변경 요약]\n"
        f"{summary}\n\n"
        "출력 형식: bullet 목록으로 요약하고, 필요하면 검토 포인트를 한 줄로 정리"
    )


def request_review(
    diff: DiffResult,
    *,
    source_name: str,
    target_name: str,
    model: str = "llama3",
    host: str = DEFAULT_HOST,
    change_limit: int = 30,
    timeout: int = 60,
) -> str:
    """Send the diff to an Ollama model and return the generated review text."""

    prompt = build_review_prompt(diff, source_name, target_name, change_limit=change_limit)
    endpoint = f"{_normalize_host(host)}/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - network dependent
        raise OllamaUnavailable(
            "Ollama 서버에 연결할 수 없습니다. `ollama serve` 또는 데몬 실행 상태를 확인하세요."
        ) from exc

    if "error" in data:
        raise OllamaUnavailable(data["error"])

    content = data.get("response")
    if not content:
        raise OllamaUnavailable("Ollama 응답에 콘텐츠가 없습니다.")

    return content.strip()


def ensure_ollama_cli(binary: str = "ollama") -> None:
    """Ensure the Ollama CLI is available on PATH before calling the API."""

    if shutil.which(binary):
        return
    raise OllamaUnavailable(
        "Ollama CLI를 찾을 수 없습니다. https://ollama.com/download 에서 설치 후 `ollama serve`를 실행해 주세요."
    )
