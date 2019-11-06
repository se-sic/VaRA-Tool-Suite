"""
Test VaRA blame reports.
"""

import unittest
import unittest.mock as mock
from pathlib import Path

import yaml

from varats.data.reports.blame_report import (BlameReport,
                                              BlameResultFunctionEntry,
                                              BlameInstInteractions,
                                              generate_degree_tuple)

YAML_DOC_1 = """---
DocType:         BlameReport
Version:         1
...
"""

YAML_DOC_2 = """---
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


class TestBlameInstInteractions(unittest.TestCase):
    """
    Test if a blame inst interactions are correctly reconstruction from yaml.
    """
    @classmethod
    def setUpClass(cls):
        """
        Load and parse function infos from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_2)):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                insts_iter = iter(yaml_doc['result-map']['bool_exec']['insts'])
                cls.blame_interaction_1 = BlameInstInteractions(
                    next(insts_iter))
                cls.blame_interaction_2 = BlameInstInteractions(
                    next(insts_iter))

    def test_base_hash(self):
        """
        Test if base_hash is loaded correctly.
        """
        self.assertEqual(self.blame_interaction_1.base_hash,
                         '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33')

        self.assertEqual(self.blame_interaction_2.base_hash,
                         '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33')

    def test_interactions(self):
        """
        Test if interactions are loaded correctly.
        """
        self.assertEqual(self.blame_interaction_1.interacting_hashes[0],
                         'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9')

        self.assertEqual(self.blame_interaction_2.interacting_hashes[0],
                         'a387695a1a2e52dcb1c5b21e73d2fd5a6aadbaf9')
        self.assertEqual(self.blame_interaction_2.interacting_hashes[1],
                         'e8999a84efbd9c3e739bff7af39500d14e61bfbc')

    def test_amount(self):
        """
        Test if amount is loaded correctly.
        """
        self.assertEqual(self.blame_interaction_1.amount, 22)
        self.assertEqual(self.blame_interaction_2.amount, 5)


class TestResultFunctionEntry(unittest.TestCase):
    """
    Test if a result function entry is correctly reconstruction from yaml.
    """
    @classmethod
    def setUpClass(cls):
        """
        Load and parse function infos from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_2)):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.func_entry_c = BlameResultFunctionEntry(
                    'bool_exec', yaml_doc['result-map']['bool_exec'])

                cls.func_entry_cxx = BlameResultFunctionEntry(
                    '_Z7doStuffii', yaml_doc['result-map']['_Z7doStuffii'])

    def test_name(self):
        """
        Test if name is saved correctly
        """
        self.assertEqual(self.func_entry_c.name, "bool_exec")
        self.assertEqual(self.func_entry_cxx.name, "_Z7doStuffii")

    def test_demangled_name(self):
        """
        Test if demangled_name is saved correctly
        """
        self.assertEqual(self.func_entry_c.demangled_name, 'bool_exec')
        self.assertEqual(self.func_entry_cxx.demangled_name,
                         'doStuff(int, int)')

    def test_found_interactions(self):
        """
        Test if all interactions where found.
        """
        c_interaction_list = self.func_entry_c.interactions
        self.assertEqual(len(c_interaction_list), 2)
        self.assertEqual(c_interaction_list[0].base_hash,
                         '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33')
        self.assertEqual(c_interaction_list[0].amount, 22)
        self.assertEqual(c_interaction_list[1].base_hash,
                         '48f8ed5347aeb9d54e7ea041b1f8d67ffe74db33')
        self.assertEqual(c_interaction_list[1].amount, 5)

        cxx_interaction_list = self.func_entry_cxx.interactions
        self.assertEqual(cxx_interaction_list, [])


class TestBlameReport(unittest.TestCase):
    """
    Test if a blame report is correctly reconstructed from yaml.
    """
    @classmethod
    def setUpClass(cls):
        """
        Load and parse function infos from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_1 + YAML_DOC_2)):
            loaded_report = BlameReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_path(self):
        """
        Test if the path is saved correctly.
        """
        self.assertEqual(self.report.path, Path("fake_file_path"))

    def test_get_function_entry(self):
        """
        Test if we get the correct function entry.
        """
        func_entry_1 = self.report.get_blame_result_function_entry(
            'adjust_assignment_expression')
        self.assertEqual(func_entry_1.name, 'adjust_assignment_expression')
        self.assertEqual(func_entry_1.demangled_name,
                         'adjust_assignment_expression')
        self.assertNotEqual(func_entry_1.name, 'bool_exec')

        func_entry_2 = self.report.get_blame_result_function_entry(
            '_Z7doStuffii')
        self.assertEqual(func_entry_2.name, '_Z7doStuffii')
        self.assertEqual(func_entry_2.demangled_name, 'doStuff(int, int)')
        self.assertNotEqual(func_entry_2.name, 'bool_exec')

    def test_iter_function_entries(self):
        """
        Test if we can iterate over all function entries.
        """
        func_entry_iter = iter(self.report.function_entries)
        self.assertEqual(
            next(func_entry_iter).name, 'adjust_assignment_expression')
        self.assertEqual(next(func_entry_iter).name, 'bool_exec')
        self.assertEqual(next(func_entry_iter).name, '_Z7doStuffii')


class TestBlameReportHelperFunctions(unittest.TestCase):
    """
    Test if a blame report is correctly reconstruction from yaml.
    """
    @classmethod
    def setUpClass(cls):
        """
        Load and parse function infos from yaml file.
        """
        with mock.patch("builtins.open",
                        new=mock.mock_open(read_data=YAML_DOC_1 + YAML_DOC_2)):
            loaded_report = BlameReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_generate_degree_tuple(self):
        """
        Test if degree tuple generation works.
        """
        degree_tuples = generate_degree_tuple(self.report)
        self.assertEqual(degree_tuples[0], (1, 22))
        self.assertEqual(degree_tuples[1], (2, 5))
