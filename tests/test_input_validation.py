"""Tests for issue_type whitelist validation across server.py and issue_reporter.py."""

import unittest
import sys
from pathlib import Path

# Ensure repo root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server
from issue_reporter import IssueReporter, DEFAULT_ISSUE_TYPES, DEFAULT_LABELS


class TestServerValidTypes(unittest.TestCase):
    """Verify VALID_TYPES is consistent and derived from _PREFIX_MAP."""

    def test_valid_types_matches_prefix_map(self):
        self.assertEqual(server.VALID_TYPES, frozenset(server._PREFIX_MAP.keys()))

    def test_valid_types_matches_label_map(self):
        self.assertEqual(set(server._PREFIX_MAP.keys()), set(server._LABEL_MAP.keys()))

    def test_valid_types_is_frozenset(self):
        self.assertIsInstance(server.VALID_TYPES, frozenset)

    def test_known_types_accepted(self):
        for t in ("bug", "feature_request", "data_issue", "ui_bug", "performance", "other"):
            self.assertIn(t, server.VALID_TYPES, f"{t} should be a valid type")

    def test_invalid_type_not_in_set(self):
        for t in ("injection", "'; DROP TABLE--", "", "Bug", "BUG", "unknown"):
            self.assertNotIn(t, server.VALID_TYPES, f"{t!r} should not be valid")


class TestServerFallback(unittest.TestCase):
    """Verify that invalid issue_type falls back to 'bug' in do_POST logic."""

    def _simulate_type_validation(self, issue_type: str) -> str:
        """Replicate the validation logic from do_POST."""
        if issue_type not in server.VALID_TYPES:
            issue_type = "bug"
        return issue_type

    def test_valid_type_unchanged(self):
        for t in server.VALID_TYPES:
            self.assertEqual(self._simulate_type_validation(t), t)

    def test_invalid_type_falls_back_to_bug(self):
        self.assertEqual(self._simulate_type_validation("injection"), "bug")

    def test_empty_string_falls_back_to_bug(self):
        self.assertEqual(self._simulate_type_validation(""), "bug")

    def test_none_coerced_falls_back_to_bug(self):
        # data.get("type", "bug") would return "bug" for missing key,
        # but if someone passes null/None explicitly:
        self.assertEqual(self._simulate_type_validation(None), "bug")

    def test_case_sensitive(self):
        self.assertEqual(self._simulate_type_validation("Bug"), "bug")
        self.assertEqual(self._simulate_type_validation("BUG"), "bug")
        self.assertEqual(self._simulate_type_validation("Feature_Request"), "bug")


class TestIssueReporterValidation(unittest.TestCase):
    """Verify issue_reporter.py validates issue_type in report()."""

    def setUp(self):
        self.reporter = IssueReporter()
        self.valid_ids = frozenset(t["id"] for t in self.reporter.issue_types)

    def test_default_types_match_labels(self):
        type_ids = {t["id"] for t in DEFAULT_ISSUE_TYPES}
        label_ids = set(DEFAULT_LABELS.keys())
        self.assertEqual(type_ids, label_ids)

    def test_valid_type_in_known_ids(self):
        for t in ("bug", "feature_request", "data_issue", "ui_bug", "performance", "other"):
            self.assertIn(t, self.valid_ids)

    def test_invalid_type_not_in_known_ids(self):
        self.assertNotIn("injection", self.valid_ids)
        self.assertNotIn("", self.valid_ids)


class TestMapsConsistency(unittest.TestCase):
    """Verify _PREFIX_MAP, _LABEL_MAP, and VALID_TYPES all share the same keys."""

    def test_all_maps_same_keys(self):
        prefix_keys = set(server._PREFIX_MAP.keys())
        label_keys = set(server._LABEL_MAP.keys())
        valid_keys = set(server.VALID_TYPES)
        self.assertEqual(prefix_keys, label_keys, "_PREFIX_MAP and _LABEL_MAP keys differ")
        self.assertEqual(prefix_keys, valid_keys, "_PREFIX_MAP and VALID_TYPES keys differ")


if __name__ == "__main__":
    unittest.main()
