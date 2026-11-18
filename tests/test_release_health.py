"""V7.1: protect release gate from accidental removal of invariants."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release_health import REQUIRED_FILES, check_release


class ReleaseHealthTests(unittest.TestCase):
    def test_release_contract_on_checked_out_repository(self):
        report = check_release(Path(__file__).resolve().parent.parent)
        self.assertEqual(report["status"], "STATIC_RELEASE_GATE_PASSED")
        self.assertEqual(report["registered_research_models"], 7)
        self.assertEqual(report["validated_models"], 0)

    def test_missing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, "Missing release module"):
                check_release(d)

    def test_unversioned_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for filename in REQUIRED_FILES:
                (root / filename).write_text("# placeholder\n")
            with self.assertRaisesRegex(RuntimeError, "App release label"):
                check_release(root)


if __name__ == "__main__":
    unittest.main()
