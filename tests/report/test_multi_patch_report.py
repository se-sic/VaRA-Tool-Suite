"""Test MultiPatchReport."""

import unittest
from pathlib import Path

from varats.provider.patch.patch_provider import Patch
from varats.report.multi_patch_report import MultiPatchReport


class TestMultiPatchReport(unittest.TestCase):
    """Tests if the basic components of MultiPatchReport are working."""

    def test_baseline_report_name(self) -> None:
        """Tests if baseline report names are correctly created and checked."""
        baseline_report_name = MultiPatchReport.create_baseline_report_name(
            "my_base.txt"
        )

        self.assertEqual(baseline_report_name, "baseline_my_base.txt")
        self.assertTrue(
            MultiPatchReport.is_baseline_report(baseline_report_name)
        )

        self.assertFalse(
            MultiPatchReport.is_baseline_report(baseline_report_name[1:])
        )

    def test_patched_report_name(self) -> None:
        """Tests if patched report names are correctly created and checked."""
        patch_shortname = "shortname"
        patch = Patch("MyPatch", patch_shortname, "desc", Path())
        patched_report_name = MultiPatchReport.create_patched_report_name(
            patch, "my_base.txt"
        )

        self.assertEqual(
            patched_report_name,
            f"patched_{len(patch_shortname)}_{patch_shortname}_my_base.txt"
        )
        self.assertTrue(MultiPatchReport.is_patched_report(patched_report_name))
        self.assertFalse(
            MultiPatchReport.is_baseline_report(patched_report_name)
        )

        self.assertFalse(
            MultiPatchReport.is_baseline_report(patched_report_name[1:])
        )

    def test_patched_report_parsing(self) -> None:
        """Test if we can correctly parse patch shortnames."""
        patch_shortname = "shortname"
        patch = Patch("MyPatch", patch_shortname, "desc", Path())
        patched_report_name = MultiPatchReport.create_patched_report_name(
            patch, "my_base.txt"
        )

        self.assertEqual(
            MultiPatchReport.
            _parse_patch_shorthand_from_report_name(patched_report_name),
            patch_shortname
        )

    def test_patched_report_parsing_with_extra_underscores(self) -> None:
        """Test special parsing case where the patch shortname contains
        underscores."""
        patch_shortname = "sh_ort_name"
        patch = Patch("MyPatch", patch_shortname, "desc", Path())
        patched_report_name = MultiPatchReport.create_patched_report_name(
            patch, "my_base.txt"
        )

        self.assertEqual(
            MultiPatchReport.
            _parse_patch_shorthand_from_report_name(patched_report_name),
            patch_shortname
        )
