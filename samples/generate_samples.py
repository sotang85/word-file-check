"""Generate sample DOCX fixtures for the lexdiff CLI."""
from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent

SAMPLES = {
    "test1": {
        "A": [
            "LexDiff는 문장 비교 도구입니다.",
            "이 문장은 그대로 유지됩니다.",
            "초기 버전은 1.2입니다.",
            "이 문장은 삭제 대상입니다.",
        ],
        "B": [
            "LexDiff는 세밀한 문장 비교 도구입니다.",
            "이 문장은 그대로 유지됩니다.",
            "초기 버전은 1.5입니다.",
            "새로운 문장도 포함됩니다.",
        ],
    },
    "test2": {
        "A": [
            "The quick brown fox jumps over the lazy dog.",
            "Spacing   matters sometimes.",
            "Budget total: 1,000 USD.",
        ],
        "B": [
            "The quick brown fox leaps over the lazy dog.",
            "Spacing matters sometimes.",
            "Budget total: 1,250 USD.",
            "Appendix A lists additional requirements.",
        ],
    },
    "test3": {
        "A": [
            "프로젝트 일정은 2023년 3월 1일에 시작합니다.",
            "테스트 커버리지는 80% 이상이어야 합니다.",
            "마감일은 4월 30일입니다.",
        ],
        "B": [
            "프로젝트 일정은 2023년 3월 1일에 시작합니다.",
            "테스트 커버리지는 85% 이상이어야 합니다.",
            "마감일은 5월 5일로 연기되었습니다.",
            "QA 팀은 주간 리포트를 제출합니다.",
        ],
    },
}


def build_document(lines: list[str]) -> Document:
    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    return doc


def generate_samples(force: bool = False) -> None:
    for case_name, variants in SAMPLES.items():
        case_dir = ROOT / case_name / "input"
        case_dir.mkdir(parents=True, exist_ok=True)
        for label, paragraphs in variants.items():
            file_path = case_dir / f"{label}.docx"
            if file_path.exists() and not force:
                continue
            document = build_document(paragraphs)
            document.save(file_path)
            print(f"Wrote {file_path.relative_to(PROJECT_ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing DOCX files if they are already present.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_samples(force=args.force)


if __name__ == "__main__":
    main()
