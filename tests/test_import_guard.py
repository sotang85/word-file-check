import tempfile
import unittest
from pathlib import Path

from lexdiff._import_guard import ensure_tree_clean


class ImportGuardTests(unittest.TestCase):
    def test_ignores_non_marker_equals_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            safe_file = root / "sample.py"
            safe_file.write_text(
                "lexdiff 소스에 병합 충돌 표식(======= 등)이 남아 있어 실행할 수 없습니다.",
                encoding="utf-8",
            )

            # Should not raise because the equals signs are not conflict markers at line start.
            ensure_tree_clean(root)

    def test_detects_conflict_markers(self) -> None:
        """Ensure true merge markers inside files are detected.

        The conflict markers are composed from parts so this test file
        itself does not trigger the import guard when scanning the tree.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            conflict_file = root / "broken.py"

            # Compose marker tokens to avoid literal conflict lines in this
            # source file, which would confuse the repo-wide import guard.
            marker_start = "<<<<<<<" + " HEAD"
            marker_mid = "======="
            marker_end = ">>>>>>>" + " branch"

            conflict_file.write_text(
                "\n".join(
                    [
                        "print('before')",
                        marker_start,
                        "print('ours')",
                        marker_mid,
                        "print('theirs')",
                        marker_end,
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                ensure_tree_clean(root)

    def test_ignored_paths_allow_local_fixtures(self) -> None:
        """Paths passed via ``ignore`` are skipped during the scan."""

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ignored = root / "tests" / "fixture_with_markers.py"
            ignored.parent.mkdir(parents=True)

            # Write a real conflict marker into the ignored file; it should be skipped.
            ignored.write_text("<<<<<<< ours\nshared\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")

            # Without ignore, the conflict would be detected.
            with self.assertRaises(SystemExit):
                ensure_tree_clean(root, ignore=())

            # With an explicit ignore entry, the scan should pass.
            ensure_tree_clean(root, ignore=(Path("tests") / "fixture_with_markers.py",))

    def test_ignored_by_filename(self) -> None:
        """Files named test_import_guard.py are skipped by default to avoid false hits."""

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "subdir" / "test_import_guard.py"
            nested.parent.mkdir(parents=True)

            # Even with a real conflict marker, the filename-based ignore should skip it.
            nested.write_text("<<<<<<< ours\nshared\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")

            # Scan should succeed because filename matches the default ignore list.
            ensure_tree_clean(root)


if __name__ == "__main__":
    unittest.main()
