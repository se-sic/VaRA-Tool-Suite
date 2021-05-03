"""Test SZZ reports."""

import unittest
import unittest.mock as mock
from pathlib import Path

from varats.data.reports.szz_report import SZZReport, SZZUnleashedReport

YAML_DOC_HEADER = """---
DocType:         SZZReport
Version:         1
...
"""

YAML_DOC_SZZ_REPORT = """---
szz_tool: SZZUnleashed
bugs:
  00e53c362677ba9363e89e859a54027581c60cf2:
  - 4795b2913b85d70dd506d743ef7cb254e875b7a7
  - e8999a84efbd9c3e739bff7af39500d14e61bfbc
  - 161147db93d306ce1337329283fe85ff6ab990ce
  029c5c8aaa410aa7ddb2bdf192201af4672e5af6:
  - e8999a84efbd9c3e739bff7af39500d14e61bfbc
  02dc0af07eb7c08ca7644c29e9aaa779ee591da9:
  - e8999a84efbd9c3e739bff7af39500d14e61bfbc
  - 9231f9e1a7d52712a06390ece55a30fe0d60677a
  - fa26077135ea9102195980a9ae3fc2ec686f84ba
  03c85e21e9bd47bb5807bb26981ffea3c1cabb35:
  - e8999a84efbd9c3e739bff7af39500d14e61bfbc
  044192441e84eeec24b50028a4293f7d1e99e5cb:
  - e8999a84efbd9c3e739bff7af39500d14e61bfbc
...
"""


class TestBlameReport(unittest.TestCase):
    """Test if a szz report is correctly reconstructed from yaml."""

    report: SZZReport

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER + YAML_DOC_SZZ_REPORT)
        ):
            loaded_report = SZZUnleashedReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_path(self):
        """Test if the path is saved correctly."""
        self.assertEqual(self.report.path, Path("fake_file_path"))

    def test_get_all_raw_bugs(self):
        """Test if we get all bugs."""
        bugs = self.report.get_all_raw_bugs()

        self.assertEqual(len(bugs), 5)

    def test_get_raw_bug_by_fix(self):
        """Test if we get the correct bugs."""
        bug1 = self.report.get_raw_bug_by_fix(
            "029c5c8aaa410aa7ddb2bdf192201af4672e5af6"
        )
        self.assertIsNotNone(bug1)
        if bug1:
            self.assertEqual(len(bug1.introducing_commits), 1)
            self.assertEqual(
                bug1.fixing_commit, "029c5c8aaa410aa7ddb2bdf192201af4672e5af6"
            )
            self.assertIn(
                "e8999a84efbd9c3e739bff7af39500d14e61bfbc",
                bug1.introducing_commits
            )

        bug2 = self.report.get_raw_bug_by_fix(
            "02dc0af07eb7c08ca7644c29e9aaa779ee591da9"
        )
        self.assertIsNotNone(bug2)
        if bug2:
            self.assertEqual(
                bug2.fixing_commit, "02dc0af07eb7c08ca7644c29e9aaa779ee591da9"
            )
            self.assertEqual(len(bug2.introducing_commits), 3)
            self.assertIn(
                "e8999a84efbd9c3e739bff7af39500d14e61bfbc",
                bug2.introducing_commits
            )
            self.assertIn(
                "9231f9e1a7d52712a06390ece55a30fe0d60677a",
                bug2.introducing_commits
            )
            self.assertIn(
                "fa26077135ea9102195980a9ae3fc2ec686f84ba",
                bug2.introducing_commits
            )
