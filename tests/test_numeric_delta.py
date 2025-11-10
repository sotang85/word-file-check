import unittest

from lexdiff import annotate_numeric_delta


class NumericDeltaTests(unittest.TestCase):
    def test_handles_thousand_separators(self) -> None:
        revised = annotate_numeric_delta("Budget total: 1,000 USD.", "Budget total: 1,250 USD.")
        self.assertEqual("Budget total: 1,250 USD. (Δ +250)", revised)

    def test_handles_negative_and_decimal_numbers(self) -> None:
        revised = annotate_numeric_delta("변경 전 값은 -1,234.5 입니다.", "변경 후 값은 -1,200.0 입니다.")
        self.assertEqual("변경 후 값은 -1,200.0 입니다. (Δ +34.5)", revised)


if __name__ == "__main__":
    unittest.main()
