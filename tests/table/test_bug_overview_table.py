"""Test bug overview table."""
import re
import unittest

from varats.paper.case_study import CaseStudy
from varats.projects.test_projects.bug_provider_test_repos import (
    BasicBugDetectionTestRepo,
)
from varats.table.tables import TableConfig, TableFormat
from varats.tables.bug_overview_table import BugOverviewTable


class TestBugOverviewTable(unittest.TestCase):
    """Test whether bug provider data gets displayed correctly for different
    formats of the table."""

    def test_basic_repo_latex_booktabs(self) -> None:
        """"Tests the latex booktabs format of the basic bug detection test
        repo."""

        # latex booktabs is default format
        table = BugOverviewTable(
            TableConfig.from_kwargs(view=False),
            case_study=CaseStudy(BasicBugDetectionTestRepo.NAME, 1)
        )

        # each bug must be matched separately since order is unclear
        result_bug_regex =\
            re.compile(
                       r"&\s*3b76c8d295385358375fefdb0cf045d97ad2d193\s*"
                       r"&\s*Multiplication result fix\\textbackslash n \s*"
                       r"&\s*VaRA Tester\s*"
                       r"&\s*None\s*\\\\\s*", re.DOTALL)
        type_bug_regex = \
            re.compile(r"&\s*2da78b2820370f6759e9086fad74155d6655e93b\s*"
                       r"&\s*Fixes return type of multiply\\textbackslash n \s*"
                       r"&\s*VaRA Tester\s*"
                       r"&\s*None\s*\\\\\s*", re.DOTALL)
        string_bug_regex = \
            re.compile(r"&\s*d846bdbe45e4d64a34115f5285079e1b5f84007f\s*"
                       r"&\s*Fixes answer to everything\\textbackslash n \s*"
                       r"&\s*VaRA Tester\s*"
                       r"&\s*None\s*\\\\\s*", re.DOTALL)
        arg_bug_regex = \
            re.compile(r"&\s*ddf0ba95408dc5508504c84e6616c49128410389\s*"
                       r"&\s*Fixed function arguments\\textbackslash n \s*"
                       r"&\s*VaRA Tester\s*"
                       r"&\s*None\s*\\\\.*", re.DOTALL)

        table_string = table.tabulate(TableFormat.LATEX_BOOKTABS, False)

        result_match = re.search(result_bug_regex, table_string)
        type_match = re.search(type_bug_regex, table_string)
        string_match = re.search(string_bug_regex, table_string)
        arg_match = re.search(arg_bug_regex, table_string)

        self.assertIsNotNone(result_match)
        self.assertIsNotNone(type_match)
        self.assertIsNotNone(string_match)
        self.assertIsNotNone(arg_match)
