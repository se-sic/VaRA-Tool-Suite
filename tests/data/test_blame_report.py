"""Test VaRA blame reports."""

import unittest
import unittest.mock as mock
from pathlib import Path

import yaml

from varats.data.reports.blame_report import (
    BlameReport,
    BlameReportDiff,
    BlameResultFunctionEntry,
    BlameInstInteractions,
    generate_degree_tuples,
)

FAKE_REPORT_PATH = (
    "BR-xz-xz-fdbc0cfa71_63959faf-66d9-41e0-8dbb-abeee2c255eb_success.yaml"
)

YAML_DOC_HEADER = """---
DocType:         BlameReport
Version:         1
...
"""

YAML_DOC_BR_1 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    insts:           []
  bool_exec:
    demangled-name:  bool_exec
    insts:
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
        amount:          22
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
          - e8999a84efbd9c3e739bff7af39500d14e61bfbc
        amount:          5
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    insts:           []
...
"""

YAML_DOC_BR_2 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    insts:           []
  bool_exec:
    demangled-name:  bool_exec
    insts:
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
        amount:          19
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
          - e8999a84efbd9c3e739bff7af39500d14e61bfbc
        amount:          7
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    insts:
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
        amount:          3
  _Z7doStuffdd:
    demangled-name:  'doStuff(double, double)'
    insts:
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
        amount:          2
...
"""

YAML_DOC_BR_3 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    insts:           []
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    insts:           []
...
"""

YAML_DOC_BR_4 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    insts:           []
  bool_exec:
    demangled-name:  bool_exec
    insts:
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
          - e8999a84efbd9c3e739bff7af39500d14e61bfbc
        amount:          5
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    insts:           []
...
"""

YAML_DOC_HEADER_2 = """---
DocType:         BlameReport
Version:         2
...
"""

YAML_DOC_BR_5 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    insts:           []
  bool_exec:
    demangled-name:  bool_exec
    insts:
      - base-hash:       48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33-xz
        interacting-hashes:
          - a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9
          - e8999a84efbd9c3e739bff7af39500d14e61bfbc-gzip
        amount:          5
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    insts:           []
...
"""


class TestBlameInstInteractions(unittest.TestCase):
    """Test if a blame inst interactions are correctly reconstruction from
    yaml."""

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_BR_1)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                insts_iter = iter(yaml_doc['result-map']['bool_exec']['insts'])
                cls.blame_interaction_1 = (
                    BlameInstInteractions.create_blame_inst_interactions(
                        next(insts_iter)
                    )
                )
                cls.blame_interaction_2 = (
                    BlameInstInteractions.create_blame_inst_interactions(
                        next(insts_iter)
                    )
                )

    def test_base_hash(self):
        """Test if base_hash is loaded correctly."""
        self.assertEqual(
            self.blame_interaction_1.base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(
            self.blame_interaction_1.base_commit.repository_name, 'Unknown'
        )

        self.assertEqual(
            self.blame_interaction_2.base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(
            self.blame_interaction_2.base_commit.repository_name, 'Unknown'
        )

    def test_interactions(self):
        """Test if interactions are loaded correctly."""
        self.assertEqual(
            self.blame_interaction_1.interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(
            self.blame_interaction_1.interacting_commits[0].repository_name,
            'Unknown'
        )

        self.assertEqual(
            self.blame_interaction_2.interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(
            self.blame_interaction_2.interacting_commits[0].repository_name,
            'Unknown'
        )
        self.assertEqual(
            self.blame_interaction_2.interacting_commits[1].commit_hash,
            'e8999a84efbd9c3e739bff7af39500d14e61bfbc'
        )
        self.assertEqual(
            self.blame_interaction_2.interacting_commits[1].repository_name,
            'Unknown'
        )

    def test_amount(self):
        """Test if amount is loaded correctly."""
        self.assertEqual(self.blame_interaction_1.amount, 22)
        self.assertEqual(self.blame_interaction_2.amount, 5)


class TestResultFunctionEntry(unittest.TestCase):
    """Test if a result function entry is correctly reconstruction from yaml."""

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_BR_1)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.func_entry_c = (
                    BlameResultFunctionEntry.create_blame_result_function_entry(
                        'bool_exec', yaml_doc['result-map']['bool_exec']
                    )
                )

                cls.func_entry_cxx = (
                    BlameResultFunctionEntry.create_blame_result_function_entry(
                        '_Z7doStuffii', yaml_doc['result-map']['_Z7doStuffii']
                    )
                )

    def test_name(self):
        """Test if name is saved correctly."""
        self.assertEqual(self.func_entry_c.name, "bool_exec")
        self.assertEqual(self.func_entry_cxx.name, "_Z7doStuffii")

    def test_demangled_name(self):
        """Test if demangled_name is saved correctly."""
        self.assertEqual(self.func_entry_c.demangled_name, 'bool_exec')
        self.assertEqual(
            self.func_entry_cxx.demangled_name, 'doStuff(int, int)'
        )

    def test_found_interactions(self):
        """Test if all interactions where found."""
        c_interaction_list = self.func_entry_c.interactions
        self.assertEqual(len(c_interaction_list), 2)
        self.assertEqual(
            c_interaction_list[0].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(c_interaction_list[0].amount, 22)
        self.assertEqual(
            c_interaction_list[1].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(c_interaction_list[1].amount, 5)

        cxx_interaction_list = self.func_entry_cxx.interactions
        self.assertEqual(cxx_interaction_list, [])


class TestBlameReport(unittest.TestCase):
    """Test if a blame report is correctly reconstructed from yaml."""

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER + YAML_DOC_BR_1)
        ):
            loaded_report = BlameReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_path(self):
        """Test if the path is saved correctly."""
        self.assertEqual(self.report.path, Path("fake_file_path"))

    def test_get_function_entry(self):
        """Test if we get the correct function entry."""
        func_entry_1 = self.report.get_blame_result_function_entry(
            'adjust_assignment_expression'
        )
        self.assertEqual(func_entry_1.name, 'adjust_assignment_expression')
        self.assertEqual(
            func_entry_1.demangled_name, 'adjust_assignment_expression'
        )
        self.assertNotEqual(func_entry_1.name, 'bool_exec')

        func_entry_2 = self.report.get_blame_result_function_entry(
            '_Z7doStuffii'
        )
        self.assertEqual(func_entry_2.name, '_Z7doStuffii')
        self.assertEqual(func_entry_2.demangled_name, 'doStuff(int, int)')
        self.assertNotEqual(func_entry_2.name, 'bool_exec')

    def test_iter_function_entries(self):
        """Test if we can iterate over all function entries."""
        func_entry_iter = iter(self.report.function_entries)
        self.assertEqual(
            next(func_entry_iter).name, 'adjust_assignment_expression'
        )
        self.assertEqual(next(func_entry_iter).name, 'bool_exec')
        self.assertEqual(next(func_entry_iter).name, '_Z7doStuffii')


class TestBlameReportWithRepoData(unittest.TestCase):
    """Test if a blame report, containing repo data , is correctly reconstructed
    from yaml."""

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER_2 + YAML_DOC_BR_5)
        ):
            loaded_report = BlameReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_get_unknown_repo_if_no_data_was_provided(self):
        """Checks if hashes without repo data get parsed correctly."""
        entry = self.report.get_blame_result_function_entry("bool_exec")
        interaction = entry.interactions[0]

        self.assertEqual(
            interaction.interacting_commits[0].commit_hash,
            "a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9"
        )
        self.assertEqual(
            interaction.interacting_commits[0].repository_name, "Unknown"
        )

    def test_correct_repo_interacting(self):
        """Checks if hashes without repo data get parsed correctly."""
        entry = self.report.get_blame_result_function_entry("bool_exec")
        interaction = entry.interactions[0]

        self.assertEqual(
            interaction.interacting_commits[1].commit_hash,
            "e8999a84efbd9c3e739bff7af39500d14e61bfbc"
        )
        self.assertEqual(
            interaction.interacting_commits[1].repository_name, "gzip"
        )

    def test_correct_repo_base_hash(self):
        """Checks if hashes without repo data get parsed correctly."""
        entry = self.report.get_blame_result_function_entry("bool_exec")
        interaction = entry.interactions[0]

        self.assertEqual(
            interaction.base_commit.commit_hash,
            "48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33"
        )
        self.assertEqual(interaction.base_commit.repository_name, "xz")


class TestBlameReportDiff(unittest.TestCase):
    """Test if diffs between BlameReports are correctly computed."""

    @classmethod
    def setUpClass(cls):
        """Load different blame_reports."""
        cls.reports = []
        for report_yaml in [
            YAML_DOC_BR_1, YAML_DOC_BR_2, YAML_DOC_BR_3, YAML_DOC_BR_4
        ]:
            with mock.patch(
                "builtins.open",
                new=mock.mock_open(read_data=YAML_DOC_HEADER + report_yaml)
            ):
                cls.reports.append(BlameReport(Path(FAKE_REPORT_PATH)))

    def test_add_function_between_reports(self):
        """Checks if the diff containts functions that where added between
        reports."""
        diff = BlameReportDiff(self.reports[1], self.reports[0])
        new_func = diff.get_blame_result_function_entry('_Z7doStuffdd')

        # Check if new function is correctly added to diff
        self.assertEqual(new_func.name, '_Z7doStuffdd')
        self.assertEqual(new_func.demangled_name, 'doStuff(double, double)')
        self.assertEqual(len(new_func.interactions), 1)
        self.assertEqual(
            new_func.interactions[0].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(len(new_func.interactions[0].interacting_commits), 1)
        self.assertEqual(
            new_func.interactions[0].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(new_func.interactions[0].amount, 2)

    def test_remove_function_between_reports(self):
        """Checks if the diff containts functions that where removed between
        reports."""
        diff = BlameReportDiff(self.reports[2], self.reports[0])
        del_func = diff.get_blame_result_function_entry('bool_exec')

        # Check if deleted function is correctly added to diff
        self.assertEqual(del_func.name, 'bool_exec')
        self.assertEqual(del_func.demangled_name, 'bool_exec')
        self.assertEqual(len(del_func.interactions), 2)
        # Check first interaction
        self.assertEqual(
            del_func.interactions[0].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(len(del_func.interactions[0].interacting_commits), 1)
        self.assertEqual(
            del_func.interactions[0].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(del_func.interactions[0].amount, 22)

        # Check second interaction
        self.assertEqual(
            del_func.interactions[1].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(len(del_func.interactions[1].interacting_commits), 2)
        self.assertEqual(
            del_func.interactions[1].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(
            del_func.interactions[1].interacting_commits[1].commit_hash,
            'e8999a84efbd9c3e739bff7af39500d14e61bfbc'
        )
        self.assertEqual(del_func.interactions[1].amount, 5)

    def test_add_interaction(self):
        """Checks if the diff containts interactions that where added between
        reports."""
        diff = BlameReportDiff(self.reports[1], self.reports[0])
        changed_func = diff.get_blame_result_function_entry('_Z7doStuffii')

        # Check if changed function is correctly added to diff
        self.assertEqual(changed_func.name, '_Z7doStuffii')
        self.assertEqual(changed_func.demangled_name, 'doStuff(int, int)')
        self.assertEqual(len(changed_func.interactions), 1)
        # Check first interaction
        self.assertEqual(
            changed_func.interactions[0].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(
            len(changed_func.interactions[0].interacting_commits), 1
        )
        self.assertEqual(
            changed_func.interactions[0].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(changed_func.interactions[0].amount, 3)

    def test_remove_interaction(self):
        """Checkfs if the diff contains interactions that where removed between
        reports."""
        diff = BlameReportDiff(self.reports[3], self.reports[0])
        del_func = diff.get_blame_result_function_entry('bool_exec')

        # Check if deleted function is correctly added to diff
        self.assertEqual(del_func.name, 'bool_exec')
        self.assertEqual(del_func.demangled_name, 'bool_exec')
        self.assertEqual(len(del_func.interactions), 1)
        # Check first interaction
        self.assertEqual(
            del_func.interactions[0].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(len(del_func.interactions[0].interacting_commits), 1)
        self.assertEqual(
            del_func.interactions[0].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(del_func.interactions[0].amount, 22)

    def test_increase_interaction_amount(self):
        """Checks if interactions where the amount increased between reports are
        shown."""
        diff = BlameReportDiff(self.reports[1], self.reports[0])
        changed_func = diff.get_blame_result_function_entry('bool_exec')

        # Check if deleted function is correctly added to diff
        self.assertEqual(changed_func.name, 'bool_exec')
        self.assertEqual(changed_func.demangled_name, 'bool_exec')
        self.assertEqual(len(changed_func.interactions), 2)

        # Check second interaction, that was increased
        self.assertEqual(
            changed_func.interactions[1].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(
            len(changed_func.interactions[1].interacting_commits), 2
        )
        self.assertEqual(
            changed_func.interactions[1].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(
            changed_func.interactions[1].interacting_commits[1].commit_hash,
            'e8999a84efbd9c3e739bff7af39500d14e61bfbc'
        )
        self.assertEqual(changed_func.interactions[1].amount, 2)

    def test_decreased_interaction_amount(self):
        """Checks if interactions where the amount decreased between reports are
        shown."""
        diff = BlameReportDiff(self.reports[1], self.reports[0])
        changed_func = diff.get_blame_result_function_entry('bool_exec')

        # Check if deleted function is correctly added to diff
        self.assertEqual(changed_func.name, 'bool_exec')
        self.assertEqual(changed_func.demangled_name, 'bool_exec')
        self.assertEqual(len(changed_func.interactions), 2)

        # Check first interaction, that was decreased
        self.assertEqual(
            changed_func.interactions[0].base_commit.commit_hash,
            '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33'
        )
        self.assertEqual(
            len(changed_func.interactions[0].interacting_commits), 1
        )
        self.assertEqual(
            changed_func.interactions[0].interacting_commits[0].commit_hash,
            'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9'
        )
        self.assertEqual(changed_func.interactions[0].amount, -3)

    def test_function_not_in_diff(self):
        """Checks that only functions that changed are in the diff."""
        # Report 2
        diff = BlameReportDiff(self.reports[1], self.reports[0])
        self.assertTrue(diff.has_function('bool_exec'))
        self.assertTrue(diff.has_function('_Z7doStuffii'))
        self.assertTrue(diff.has_function('_Z7doStuffdd'))
        self.assertFalse(diff.has_function('adjust_assignment_expression'))

        # Report 3
        diff_2 = BlameReportDiff(self.reports[2], self.reports[0])
        self.assertTrue(diff_2.has_function('bool_exec'))
        self.assertFalse(diff_2.has_function('adjust_assignment_expression'))
        self.assertFalse(diff_2.has_function('_Z7doStuffii'))

        # Report 4
        diff_3 = BlameReportDiff(self.reports[3], self.reports[0])
        self.assertTrue(diff_3.has_function('bool_exec'))
        self.assertFalse(diff_3.has_function('adjust_assignment_expression'))
        self.assertFalse(diff_3.has_function('_Z7doStuffii'))


class TestBlameReportHelperFunctions(unittest.TestCase):
    """Test if a blame report is correctly reconstruction from yaml."""

    @classmethod
    def setUpClass(cls):
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_HEADER + YAML_DOC_BR_1)
        ):
            loaded_report = BlameReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_generate_degree_tuple(self):
        """Test if degree tuple generation works."""
        degree_tuples = generate_degree_tuples(self.report)
        self.assertEqual(degree_tuples[0], (1, 22))
        self.assertEqual(degree_tuples[1], (2, 5))
