import unittest

from lexdiff import DiffResult, Operation, Sentence
from lexdiff.ollama import build_change_summary, build_review_prompt


class OllamaPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sent_a = Sentence(index=0, text="원문 첫 문장", paragraph_index=0, sentence_in_paragraph=0)
        self.sent_b = Sentence(index=1, text="수정된 첫 문장", paragraph_index=0, sentence_in_paragraph=0)
        self.sent_c = Sentence(index=2, text="추가 문장", paragraph_index=1, sentence_in_paragraph=0)

    def test_summary_truncates_and_counts(self) -> None:
        operations = [
            Operation(kind="replace", similarity=0.9, original=self.sent_a, revised=self.sent_b),
            Operation(kind="add", similarity=0.0, revised=self.sent_c),
            Operation(kind="equal", similarity=1.0, original=self.sent_a, revised=self.sent_a),
        ]
        summary = build_change_summary(operations, limit=1)
        self.assertIn("1. [replace]", summary)
        self.assertIn("... 1개 변경이 더 있습니다.", summary)

    def test_prompt_contains_context(self) -> None:
        operations = [Operation(kind="add", similarity=0.0, revised=self.sent_c)]
        diff = DiffResult(operations=operations, rows=[])
        prompt = build_review_prompt(diff, "A.docx", "B.docx", change_limit=5)
        self.assertIn("원본 문서: A.docx", prompt)
        self.assertIn("수정 문서: B.docx", prompt)
        self.assertIn("추가 문장", prompt)
        self.assertIn("bullet", prompt)


if __name__ == "__main__":
    unittest.main()
