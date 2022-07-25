"""Test VaRA feature analysis reports."""

import typing as tp
import unittest
import unittest.mock as mock
from pathlib import Path

import yaml

from varats.data.reports.feature_analysis_report import (
    FeatureAnalysisGroundTruth,
    FeatureAnalysisReport,
    FeatureAnalysisReportEval,
    FeatureAnalysisReportMetaData,
    FeatureAnalysisResultFunctionEntry,
    FeatureTaintedInstruction,
)

YAML_DOC_HEADER = """---
DocType:         FeatureAnalysisReport
Version:         1
...
"""

YAML_DOC_FAR_METADATA = """---
funcs-in-module: 3
insts-in-module: 21
br-switch-insts-in-module: 9
...
"""

YAML_DOC_FAR_1 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    feature-related-insts: []
  bool_exec:
    demangled-name:  bool_exec
    feature-related-insts:
      - inst:       '%foo = alloca i8, align 1, !FVar !4224'
        location:   None
        taints:
          - foo
      - inst:       'br i1 %tobool, label %if.then, label %if.else, !dbg !666'
        location:   'src/path/example.cpp:42'
        taints:
          - foo
          - test
          - feature
      - inst:       'switch i32 %2, label %sw.epilog [\n    i32 0, label %sw.bb\n  ], !dbg !1945'
        location:   'src/path/example.cpp:50'
        taints:
          - feature
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    feature-related-insts: []
...
"""

YAML_DOC_FAR_2 = """---
result-map:
  adjust_assignment_expression:
    demangled-name:  adjust_assignment_expression
    feature-related-insts: []
  bool_exec:
    demangled-name:  bool_exec
    feature-related-insts:
      - inst:       'br i1 %tobool, label %if.then, label %if.else, !dbg !666'
        location:   'src/path/example.cpp:42'
        taints:
          - foo
          - test
      - inst:       'br i1 %tobool, label %if.then1, label %if.else2, !dbg !69'
        location:   'src/path/example.cpp:42'
        taints:
          - foo
          - test
      - inst:       'br i1 %tobool, label %if.then2, label %if.else3, !dbg !669'
        location:   'src/path/example.cpp:42'
        taints:
          - test
  _Z7doStuffii:
    demangled-name:  'doStuff(int, int)'
    feature-related-insts: []
...
"""

YAML_DOC_GT_1 = """---
foo:
    - 'src/path/example.cpp:42'
    - 'src/path/example.cpp:70'
test:
    - 'src/path/example.cpp:24'
    - 'src/path/file.cpp:9'
feature:
    - 'src/path/example.cpp:42'
...
"""

YAML_DOC_GT_2 = """---
foo:
    - 'src/path/example.cpp:42'
test:
    - 'src/path/example.cpp:24'
feature:
    - 'src/path/example.cpp:42'
...
"""


class TestFeatureTaintedInstruction(unittest.TestCase):
    """Test if a feature tainted instruction is correctly reconstructed from
    yaml."""

    feature_tainted_inst_1: FeatureTaintedInstruction
    feature_tainted_inst_2: FeatureTaintedInstruction
    feature_tainted_inst_3: FeatureTaintedInstruction

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_FAR_1)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                insts_iter = iter(
                    yaml_doc['result-map']['bool_exec']['feature-related-insts']
                )
                cls.feature_tainted_inst_1 = (
                    FeatureTaintedInstruction.
                    create_feature_tainted_instruction(next(insts_iter))
                )
                cls.feature_tainted_inst_2 = (
                    FeatureTaintedInstruction.
                    create_feature_tainted_instruction(next(insts_iter))
                )
                cls.feature_tainted_inst_3 = (
                    FeatureTaintedInstruction.
                    create_feature_tainted_instruction(next(insts_iter))
                )

    def test_instructions(self) -> None:
        """Test if instruction is loaded correctly."""
        self.assertEqual(
            self.feature_tainted_inst_1.instruction,
            '%foo = alloca i8, align 1, !FVar !4224'
        )
        self.assertEqual(
            self.feature_tainted_inst_2.instruction,
            'br i1 %tobool, label %if.then, label %if.else, !dbg !666'
        )

    def test_locations(self) -> None:
        """Test if location is loaded correctly."""
        self.assertEqual(self.feature_tainted_inst_1.location, 'None')
        self.assertEqual(
            self.feature_tainted_inst_2.location, 'src/path/example.cpp:42'
        )

    def test_taints(self) -> None:
        """Test if taints are loaded correctly."""
        feature_taints_1 = self.feature_tainted_inst_1.feature_taints
        self.assertEqual(len(feature_taints_1), 1)
        self.assertEqual(feature_taints_1[0], 'foo')

        feature_taints_2 = self.feature_tainted_inst_2.feature_taints
        self.assertEqual(len(feature_taints_2), 3)
        self.assertEqual(feature_taints_2[0], 'feature')
        self.assertEqual(feature_taints_2[1], 'foo')
        self.assertEqual(feature_taints_2[2], 'test')

    def test_is_terminator(self) -> None:
        """Test if br and switch instructions are correctly identified."""
        self.assertFalse(self.feature_tainted_inst_1.is_terminator())
        self.assertTrue(self.feature_tainted_inst_2.is_terminator())
        self.assertTrue(self.feature_tainted_inst_3.is_terminator())


class TestFeatureAnalysisResultFunctionEntry(unittest.TestCase):
    """Test if a result function entry is correctly reconstructed from yaml."""

    func_entry_1: FeatureAnalysisResultFunctionEntry
    func_entry_2: FeatureAnalysisResultFunctionEntry

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_FAR_1)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.func_entry_1 = (
                    FeatureAnalysisResultFunctionEntry.
                    create_feature_analysis_result_function_entry(
                        'bool_exec', yaml_doc['result-map']['bool_exec']
                    )
                )

                cls.func_entry_2 = (
                    FeatureAnalysisResultFunctionEntry.
                    create_feature_analysis_result_function_entry(
                        '_Z7doStuffii', yaml_doc['result-map']['_Z7doStuffii']
                    )
                )

    def test_name(self) -> None:
        """Test if name is saved correctly."""
        self.assertEqual(self.func_entry_1.name, 'bool_exec')
        self.assertEqual(self.func_entry_2.name, '_Z7doStuffii')

    def test_demangled_name(self) -> None:
        """Test if demangled_name is saved correctly."""
        self.assertEqual(self.func_entry_1.demangled_name, 'bool_exec')
        self.assertEqual(self.func_entry_2.demangled_name, 'doStuff(int, int)')

    def test_tainted_insts(self) -> None:
        """Test if all feature tainted instructions are found."""
        inst_list_1 = self.func_entry_1.feature_tainted_insts
        self.assertEqual(len(inst_list_1), 3)
        self.assertEqual(
            inst_list_1[0].instruction, '%foo = alloca i8, align 1, !FVar !4224'
        )
        self.assertEqual(inst_list_1[0].location, 'None')
        self.assertEqual(inst_list_1[0].feature_taints, ['foo'])
        self.assertEqual(
            inst_list_1[1].instruction,
            'br i1 %tobool, label %if.then, label %if.else, !dbg !666'
        )
        self.assertEqual(inst_list_1[1].location, 'src/path/example.cpp:42')
        self.assertEqual(
            inst_list_1[1].feature_taints, ['feature', 'foo', 'test']
        )

        inst_list_2 = self.func_entry_2.feature_tainted_insts
        self.assertEqual(inst_list_2, [])


class TestFeatureAnalysisReportMetaData(unittest.TestCase):
    """Test if meta data from a feature analysis report is correctly
    reconstructed from yaml."""

    meta_data: FeatureAnalysisReportMetaData

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(read_data=YAML_DOC_FAR_METADATA)
        ):
            with open("fake_file_path") as yaml_file:
                yaml_doc = yaml.safe_load(yaml_file)
                cls.meta_data = FeatureAnalysisReportMetaData.create_feature_analysis_report_meta_data(
                    yaml_doc
                )

    def test_num_functions_is_parsed_correctly(self) -> None:
        """Tests if the number of functions is correctly parsed from the
        file."""
        self.assertEqual(self.meta_data.num_functions, 3)

    def test_num_instructions_is_parsed_correctly(self) -> None:
        """Tests if the number of instructions is correctly parsed from the
        file."""
        self.assertEqual(self.meta_data.num_instructions, 21)

    def test_num_br_switch_instructions_is_parsed_correctly(self) -> None:
        """Tests if the number of branch and switch instructions is correctly
        parsed from the file."""
        self.assertEqual(self.meta_data.num_br_switch_insts, 9)


class TestFeatureAnalysisReport(unittest.TestCase):
    """Test if a feature analysis report is correctly reconstructed from
    yaml."""

    report: FeatureAnalysisReport

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(
                read_data=YAML_DOC_HEADER + YAML_DOC_FAR_METADATA +
                YAML_DOC_FAR_1
            )
        ):
            loaded_report = FeatureAnalysisReport(Path('fake_file_path'))
            cls.report = loaded_report

    def test_path(self) -> None:
        """Test if the path is saved correctly."""
        self.assertEqual(self.report.path, Path("fake_file_path"))

    def test_meta_data(self) -> None:
        """Test if meta data is parsed correctly."""
        meta_data = self.report.meta_data
        self.assertEqual(meta_data.num_functions, 3)
        self.assertEqual(meta_data.num_instructions, 21)
        self.assertEqual(meta_data.num_br_switch_insts, 9)

    def test_iter_function_entries(self) -> None:
        """Test if we can iterate over all function entries."""
        func_entry_iter = iter(self.report.function_entries)
        self.assertEqual(
            next(func_entry_iter).name, 'adjust_assignment_expression'
        )
        self.assertEqual(next(func_entry_iter).name, 'bool_exec')
        self.assertEqual(next(func_entry_iter).name, '_Z7doStuffii')

    def test_get_function_entry(self) -> None:
        """Test if we get the correct function entry."""
        func_entry_1 = self.report.get_feature_analysis_result_function_entry(
            'adjust_assignment_expression'
        )
        self.assertEqual(func_entry_1.name, 'adjust_assignment_expression')
        self.assertEqual(
            func_entry_1.demangled_name, 'adjust_assignment_expression'
        )
        self.assertEqual(func_entry_1.feature_tainted_insts, [])
        self.assertNotEqual(func_entry_1.name, 'bool_exec')

        func_entry_2 = self.report.get_feature_analysis_result_function_entry(
            'bool_exec'
        )
        self.assertEqual(func_entry_2.name, 'bool_exec')
        self.assertEqual(func_entry_2.demangled_name, 'bool_exec')
        self.assertNotEqual(func_entry_2.name, 'adjust_assignment_expression')
        self.assertNotEqual(func_entry_2.name, '_Z7doStuffii')
        insts_2 = func_entry_2.feature_tainted_insts
        self.assertEqual(len(insts_2), 3)
        self.assertEqual(
            insts_2[0].instruction, '%foo = alloca i8, align 1, !FVar !4224'
        )
        self.assertEqual(insts_2[0].location, 'None')
        self.assertEqual(insts_2[0].feature_taints, ['foo'])
        self.assertEqual(
            insts_2[1].instruction,
            'br i1 %tobool, label %if.then, label %if.else, !dbg !666'
        )
        self.assertEqual(insts_2[1].location, 'src/path/example.cpp:42')
        self.assertEqual(insts_2[1].feature_taints, ['feature', 'foo', 'test'])

        func_entry_3 = self.report.get_feature_analysis_result_function_entry(
            '_Z7doStuffii'
        )
        self.assertEqual(func_entry_3.name, '_Z7doStuffii')
        self.assertEqual(func_entry_3.demangled_name, 'doStuff(int, int)')
        self.assertEqual(func_entry_3.feature_tainted_insts, [])
        self.assertNotEqual(func_entry_3.name, 'bool_exec')

    def test_get_feature_locations_dict(self) -> None:
        """Test if mapping of features to locations is correct."""
        feat_loc_dict = self.report.get_feature_locations_dict()
        self.assertEqual(len(feat_loc_dict), 3)
        self.assertEqual(feat_loc_dict['foo'], ['src/path/example.cpp:42'])
        self.assertEqual(
            feat_loc_dict['feature'],
            ['src/path/example.cpp:42', 'src/path/example.cpp:50']
        )
        self.assertEqual(feat_loc_dict['test'], ['src/path/example.cpp:42'])


class TestFeatureAnalysisGroundTruth(unittest.TestCase):
    """Test if a feature analysis ground truth is correctly reconstructed from
    yaml."""

    ground_truth: FeatureAnalysisGroundTruth

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse location infos from yaml file."""
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_GT_1)
        ):
            cls.ground_truth = FeatureAnalysisGroundTruth(
                Path('fake_file_path')
            )

    def test_path(self) -> None:
        """Test if the path is saved correctly."""
        self.assertEqual(self.ground_truth.path, Path("fake_file_path"))

    def test_get_feature_locations(self):
        """Test if the feature locations are correctly parsed."""
        foo_locations = self.ground_truth.get_feature_locations('foo')
        self.assertEqual(
            foo_locations,
            ['src/path/example.cpp:42', 'src/path/example.cpp:70']
        )

        test_locations = self.ground_truth.get_feature_locations('test')
        self.assertEqual(
            test_locations, ['src/path/example.cpp:24', 'src/path/file.cpp:9']
        )

        feature_locations = self.ground_truth.get_feature_locations('feature')
        self.assertEqual(feature_locations, ['src/path/example.cpp:42'])

    def test_get_features(self):
        """Test if we get the correct features."""
        features = self.ground_truth.get_features()
        self.assertTrue('foo' in features)
        self.assertTrue('test' in features)
        self.assertTrue('feature' in features)


class TestFeatureAnalysisReportEval(unittest.TestCase):
    """Test if the evaluation of a feature analysis report is correctly
    executed."""

    eval_1: FeatureAnalysisReportEval
    eval_2: FeatureAnalysisReportEval

    @classmethod
    def setUpClass(cls) -> None:
        """Load and parse function infos from yaml file."""
        report_1: FeatureAnalysisReport
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(
                read_data=YAML_DOC_HEADER + YAML_DOC_FAR_METADATA +
                YAML_DOC_FAR_1
            )
        ):
            report_1 = FeatureAnalysisReport(Path('fake_file_path'))
        """Load and parse location infos from yaml file."""
        ground_truth_1: FeatureAnalysisGroundTruth
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_GT_1)
        ):
            ground_truth_1 = FeatureAnalysisGroundTruth(Path('fake_file_path'))

        cls.eval_1 = FeatureAnalysisReportEval(
            report_1, ground_truth_1, ['foo', 'test', 'feature']
        )
        """Load and parse function infos from yaml file."""
        report_2: FeatureAnalysisReport
        with mock.patch(
            "builtins.open",
            new=mock.mock_open(
                read_data=YAML_DOC_HEADER + YAML_DOC_FAR_METADATA +
                YAML_DOC_FAR_2
            )
        ):
            report_2 = FeatureAnalysisReport(Path('fake_file_path'))
        """Load and parse location infos from yaml file."""
        ground_truth_2: FeatureAnalysisGroundTruth
        with mock.patch(
            "builtins.open", new=mock.mock_open(read_data=YAML_DOC_GT_2)
        ):
            ground_truth_2 = FeatureAnalysisGroundTruth(Path('fake_file_path'))

        cls.eval_2 = FeatureAnalysisReportEval(
            report_2, ground_truth_2, ['foo', 'test', 'feature']
        )

    def test_eval_stats(self) -> None:
        """Test if the statistical evaluation data is correct."""
        self.assertEqual(self.eval_1.get_true_pos('foo'), 1)
        self.assertEqual(self.eval_1.get_false_pos('foo'), 0)
        self.assertEqual(self.eval_1.get_false_neg('foo'), 1)
        self.assertEqual(self.eval_1.get_true_neg('foo'), 7)

        self.assertEqual(self.eval_1.get_true_pos('test'), 0)
        self.assertEqual(self.eval_1.get_false_pos('test'), 1)
        self.assertEqual(self.eval_1.get_false_neg('test'), 2)
        self.assertEqual(self.eval_1.get_true_neg('test'), 6)

        self.assertEqual(self.eval_1.get_true_pos('feature'), 1)
        self.assertEqual(self.eval_1.get_false_pos('feature'), 1)
        self.assertEqual(self.eval_1.get_false_neg('feature'), 0)
        self.assertEqual(self.eval_1.get_true_neg('feature'), 7)

        self.assertEqual(self.eval_1.get_true_pos(), 2)
        self.assertEqual(self.eval_1.get_false_pos(), 2)
        self.assertEqual(self.eval_1.get_false_neg(), 3)
        self.assertEqual(self.eval_1.get_true_neg(), 20)

        self.assertEqual(self.eval_2.get_true_pos('foo'), 2)
        self.assertEqual(self.eval_2.get_false_pos('foo'), 0)
        self.assertEqual(self.eval_2.get_false_neg('foo'), 0)
        self.assertEqual(self.eval_2.get_true_neg('foo'), 7)

        self.assertEqual(self.eval_2.get_true_pos('test'), 0)
        self.assertEqual(self.eval_2.get_false_pos('test'), 3)
        self.assertEqual(self.eval_2.get_false_neg('test'), 1)
        self.assertEqual(self.eval_2.get_true_neg('test'), 5)

        self.assertEqual(self.eval_2.get_true_pos('feature'), 0)
        self.assertEqual(self.eval_2.get_false_pos('feature'), 0)
        self.assertEqual(self.eval_2.get_false_neg('feature'), 1)
        self.assertEqual(self.eval_2.get_true_neg('feature'), 8)

        self.assertEqual(self.eval_2.get_true_pos(), 2)
        self.assertEqual(self.eval_2.get_false_pos(), 3)
        self.assertEqual(self.eval_2.get_false_neg(), 2)
        self.assertEqual(self.eval_2.get_true_neg(), 20)

    def test_eval_locs(self) -> None:
        """Test if the location evaluation data is correct."""
        true_pos_foo = list()
        false_pos_foo = list()
        false_neg_foo = list()
        true_pos_foo.append('src/path/example.cpp:42')
        false_neg_foo.append('src/path/example.cpp:70')
        self.assertEqual(self.eval_1.get_true_pos_locs('foo'), true_pos_foo)
        self.assertEqual(self.eval_1.get_false_pos_locs('foo'), false_pos_foo)
        self.assertEqual(self.eval_1.get_false_neg_locs('foo'), false_neg_foo)

        true_pos_test = list()
        false_pos_test = list()
        false_neg_test = list()
        false_pos_test.append('src/path/example.cpp:42')
        false_neg_test.append('src/path/example.cpp:24')
        false_neg_test.append('src/path/file.cpp:9')
        self.assertEqual(self.eval_1.get_true_pos_locs('test'), true_pos_test)
        self.assertEqual(self.eval_1.get_false_pos_locs('test'), false_pos_test)
        self.assertEqual(self.eval_1.get_false_neg_locs('test'), false_neg_test)

        true_pos_feature = list()
        false_pos_feature = list()
        false_neg_feature = list()
        true_pos_feature.append('src/path/example.cpp:42')
        false_pos_feature.append('src/path/example.cpp:50')
        self.assertEqual(
            self.eval_1.get_true_pos_locs('feature'), true_pos_feature
        )
        self.assertEqual(
            self.eval_1.get_false_pos_locs('feature'), false_pos_feature
        )
        self.assertEqual(
            self.eval_1.get_false_neg_locs('feature'), false_neg_feature
        )

        true_pos_foo = list()
        false_pos_foo = list()
        false_neg_foo = list()
        true_pos_foo.append('src/path/example.cpp:42')
        true_pos_foo.append('src/path/example.cpp:42')
        self.assertEqual(self.eval_2.get_true_pos_locs('foo'), true_pos_foo)
        self.assertEqual(self.eval_2.get_false_pos_locs('foo'), false_pos_foo)
        self.assertEqual(self.eval_2.get_false_neg_locs('foo'), false_neg_foo)

        true_pos_test = list()
        false_pos_test = list()
        false_neg_test = list()
        false_pos_test.append('src/path/example.cpp:42')
        false_pos_test.append('src/path/example.cpp:42')
        false_pos_test.append('src/path/example.cpp:42')
        false_neg_test.append('src/path/example.cpp:24')
        self.assertEqual(self.eval_2.get_true_pos_locs('test'), true_pos_test)
        self.assertEqual(self.eval_2.get_false_pos_locs('test'), false_pos_test)
        self.assertEqual(self.eval_2.get_false_neg_locs('test'), false_neg_test)

        true_pos_feature = list()
        false_pos_feature = list()
        false_neg_feature = list()
        false_neg_feature.append('src/path/example.cpp:42')
        self.assertEqual(
            self.eval_2.get_true_pos_locs('feature'), true_pos_feature
        )
        self.assertEqual(
            self.eval_2.get_false_pos_locs('feature'), false_pos_feature
        )
        self.assertEqual(
            self.eval_2.get_false_neg_locs('feature'), false_neg_feature
        )
