import shutil
import unittest
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_utils import (
    run_in_test_environment,
    UnitTestFixtures,
    TEST_INPUTS_DIR,
    LoadRepositoryForTest,
)
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CodeRegionKind,
    RegionStart,
    RegionEnd,
    CoverageReport,
    cov_show,
)
from varats.data.reports.llvm_coverage_report import (
    __cov_fill_buffer as cov_fill_buffer,
)
from varats.data.reports.llvm_coverage_report import (
    __get_next_line_and_column as get_next_line_and_column,
)
from varats.paper.paper_config import load_paper_config, get_loaded_paper_config
from varats.plot.plots import PlotConfig
from varats.plots.llvm_coverage_plot import CoveragePlotGenerator
from varats.utils.settings import vara_cfg, save_config
from varats.varats.experiments.vara.llvm_coverage_experiment import (
    GenerateCoverageExperiment,
)

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main")


class TestCodeRegion(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.CODE_REGION_1 = CodeRegion(
            RegionStart(line=9, column=79),
            RegionEnd(line=17, column=2),
            count=4,
            kind=CodeRegionKind.CODE,
            function="main"
        )
        self.CODE_REGION_2 = CodeRegion(
            RegionStart(line=9, column=80),
            RegionEnd(line=17, column=1),
            count=0,
            kind=CodeRegionKind.CODE,
            function="main"
        )
        self.CODE_REGION_1.insert(self.CODE_REGION_2)

        self.root = CodeRegion.from_list([0, 0, 100, 100, 5, 0, 0, 0], "main")
        self.left = CodeRegion.from_list([0, 1, 49, 100, 5, 0, 0, 0], "main")
        self.right = CodeRegion.from_list([50, 0, 100, 99, 5, 0, 0, 0], "main")
        self.left_left = CodeRegion.from_list([30, 0, 40, 100, 3, 0, 0, 0],
                                              "main")
        self.left_left_2 = CodeRegion.from_list([10, 0, 20, 100, 3, 0, 0, 0],
                                                "main")
        self.right_right = CodeRegion.from_list([60, 0, 80, 100, 2, 0, 0, 0],
                                                "main")

        self.root.insert(self.right)
        self.root.insert(self.left_left)
        self.root.insert(self.left_left_2)
        self.root.insert(self.left)
        self.root.insert(self.right_right)

    def test_eq(self):
        self.assertEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_1(self):
        self.CODE_REGION_1.start.line = 1
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_2(self):
        self.CODE_REGION_1.end.line = 18
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_3(self):
        self.CODE_REGION_1.end.column = 1
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_4(self):
        self.CODE_REGION_1.kind = CodeRegionKind.GAP
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_less_1(self):
        self.assertFalse(self.CODE_REGION_1 < CODE_REGION_1)
        self.assertTrue(self.CODE_REGION_1 <= CODE_REGION_1)

        self.CODE_REGION_1.start.column = 78
        self.assertTrue(self.CODE_REGION_1 < CODE_REGION_1)
        self.assertFalse(CODE_REGION_1 < self.CODE_REGION_1)

    def test_greater_1(self):
        self.assertFalse(self.CODE_REGION_1 > CODE_REGION_1)
        self.assertTrue(self.CODE_REGION_1 >= CODE_REGION_1)

        self.CODE_REGION_1.start.column = 80
        self.assertTrue(self.CODE_REGION_1 > CODE_REGION_1)
        self.assertFalse(CODE_REGION_1 > self.CODE_REGION_1)

    def test_subregions(self):
        self.assertFalse(self.CODE_REGION_1.is_subregion(self.CODE_REGION_1))

        self.assertTrue(self.CODE_REGION_1.is_subregion(self.CODE_REGION_2))
        self.assertFalse(self.CODE_REGION_2.is_subregion(self.CODE_REGION_1))

        self.CODE_REGION_1.start.line = 10
        self.CODE_REGION_2.end.column = 2
        self.assertFalse(self.CODE_REGION_1.is_subregion(self.CODE_REGION_2))
        self.assertFalse(self.CODE_REGION_2.is_subregion(self.CODE_REGION_1))

    def test_is_covered(self):
        self.assertTrue(self.CODE_REGION_1.is_covered())
        self.assertFalse(self.CODE_REGION_2.is_covered())

    def test_contains(self):
        self.assertTrue(self.CODE_REGION_2 in self.CODE_REGION_1)
        self.assertFalse(self.CODE_REGION_1 in self.CODE_REGION_2)

    def test_parent(self):
        self.assertFalse(self.CODE_REGION_1.has_parent())
        self.assertIsNone(self.CODE_REGION_1.parent)

        self.assertTrue(self.CODE_REGION_2.has_parent())
        self.assertEqual(self.CODE_REGION_2.parent, self.CODE_REGION_1)

    def test_iter_breadth_first(self):
        self.assertEqual([
            self.root, self.left, self.right, self.left_left_2, self.left_left,
            self.right_right
        ], list(self.root.iter_breadth_first()))

    def test_iter_preorder(self):
        self.assertEqual([
            self.root,
            self.left,
            self.left_left_2,
            self.left_left,
            self.right,
            self.right_right,
        ], list(self.root.iter_preorder()))

    def test_iter_postorder(self):
        self.assertEqual([
            self.left_left_2, self.left_left, self.left, self.right_right,
            self.right, self.root
        ], list(self.root.iter_postorder()))

    def test_insert(self):
        self.assertTrue(self.root.is_subregion(self.left))
        self.assertTrue(self.root.is_subregion(self.right))
        self.assertTrue(self.root.is_subregion(self.left_left))
        self.assertTrue(self.root.is_subregion(self.right_right))
        self.assertTrue(self.left.is_subregion(self.left_left))
        self.assertTrue(self.left.is_subregion(self.left_left_2))
        self.assertTrue(self.right.is_subregion(self.right_right))

        self.assertFalse(self.right.is_subregion(self.left))
        self.assertFalse(self.right.is_subregion(self.left_left))
        self.assertFalse(self.right.is_subregion(self.left_left_2))
        self.assertFalse(self.left.is_subregion(self.right))
        self.assertFalse(self.left.is_subregion(self.right_right))
        self.assertFalse(self.left.is_subregion(self.root))
        self.assertFalse(self.right.is_subregion(self.root))

        self.assertTrue(self.left.parent is self.root)
        self.assertTrue(self.right.parent is self.root)
        self.assertTrue(self.left_left.parent is self.left)
        self.assertTrue(self.left_left_2.parent is self.left)
        self.assertTrue(self.right_right.parent is self.right)

    def test_diff(self):
        root_2 = deepcopy(self.root)
        root_3 = deepcopy(self.root)

        root_2.diff(root_3)

        for x in root_2.iter_breadth_first():
            self.assertEqual(x.count, 0)

        self.left_left.count = 5
        self.left_left_2.count = 1
        self.right_right.count = 3

        self.root.diff(root_3)
        self.assertEqual(self.root.count, 0)
        self.assertEqual(self.right.count, 0)
        self.assertEqual(self.left.count, 0)
        self.assertEqual(self.left_left.count, 2)
        self.assertEqual(self.left_left_2.count, -2)
        self.assertEqual(self.right_right.count, 1)

        self.assertFalse(self.root.is_identical(root_3))

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_merging(self):
        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_coverage_plot"
        load_paper_config()
        save_config()

        plot_generator = CoveragePlotGenerator(
            PlotConfig.from_kwargs(view=False),
            experiment_type=[GenerateCoverageExperiment],
            case_study=get_loaded_paper_config().
            get_case_studies("FeaturePerfCSCollection")
        )
        plots = plot_generator.generate()
        self.assertEqual(len(plots), 1)
        coverage_plot = plots[0]

        case_studies = get_loaded_paper_config().get_all_case_studies()
        self.assertEqual(len(case_studies), 1)
        case_study = case_studies[0]

        binary_config_map = coverage_plot._get_binary_config_map(case_study)
        self.assertTrue(binary_config_map)

        config_map = binary_config_map[next(iter(binary_config_map))]
        self.assertEqual(len(config_map), 3)

        for config in config_map:
            options = [x.value for x in config.options()]
            if options == ["--slow", "--header"]:
                header_slow = config
            elif options == ["--header"]:
                header = config
            elif options == ["--slow"]:
                slow = config

        header_slow_report = config_map[header_slow]
        header_report = config_map[header]
        slow_report = config_map[slow]

        self.assertIsNot(header_slow_report, header_report)
        self.assertIsNot(header_slow_report, slow_report)
        self.assertIsNot(header_slow, slow_report)

        self.assertNotEqual(header_report, slow_report)
        self.assertNotEqual(header_slow_report, header_report)
        self.assertNotEqual(header_slow_report, slow_report)

        merged_header_slow_report_1 = deepcopy(header_report)
        merged_header_slow_report_1.merge(deepcopy(slow_report))
        merged_header_slow_report_2 = deepcopy(slow_report)
        merged_header_slow_report_2.merge(deepcopy(header_report))

        self.assertEqual(
            merged_header_slow_report_1, merged_header_slow_report_2
        )
        self.assertNotEqual(merged_header_slow_report_1, header_slow_report)

        llvm_profdata_merged_slow_and_header_report = CoverageReport.from_json(
            Path(TEST_INPUTS_DIR) / "results" / "FeaturePerfCSCollection" /
            "llvm-profdata_merged_slow_and_header.json"
        )

        self.assertNotEqual(
            llvm_profdata_merged_slow_and_header_report, header_slow_report
        )
        self.assertEqual(
            llvm_profdata_merged_slow_and_header_report,
            merged_header_slow_report_1
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_cov_show_simple(self):
        self.maxDiff = None
        with TemporaryDirectory() as tmpdir:
            shutil.unpack_archive(
                Path(TEST_INPUTS_DIR) / "results" / "FeaturePerfCSCollection" /
                "GenCov-CovR-FeaturePerfCSCollection-MultiSharedMultipleRegions-27f1708037"
                / "cca2928a-70d1-4c30-bd8e-6585f7edc9ce_config-0_success.zip",
                tmpdir
            )

            for file in Path(tmpdir).iterdir():
                if file.suffix == ".json":
                    json_file = file

            assert json_file

            slow_report = CoverageReport.from_json(json_file)

        with open(
            Path(TEST_INPUTS_DIR) / "results" / "FeaturePerfCSCollection" /
            "cov_show_slow.txt"
        ) as tmp:
            cov_show_slow_txt = tmp.read()

        with open(
            Path(TEST_INPUTS_DIR) / "results" / "FeaturePerfCSCollection" /
            "cov_show_slow_color.txt",
        ) as tmp:
            cov_show_slow_color_txt = tmp.read()

        with LoadRepositoryForTest("FeaturePerfCSCollection", "27f1708037"):
            self.assertEqual(
                cov_show_slow_txt, cov_show(slow_report, force_color=False)
            )
            output = cov_show(slow_report, force_color=True)
            # Replace different color codes.
            output = output.replace("\x1b[36m", "\x1b[0;36m").replace(
                "\x1b[39m", "\x1b[0m"
            ).replace("\x1b[0;41m",
                      "\x1b[41m").replace("\x1b[49m", "\x1b[0m"
                                         ).replace("\x1b[41m\x1b[0m", "")

            # We don't have magenta colored counts for conditions
            cov_show_slow_color_txt = cov_show_slow_color_txt.replace(
                "\x1b[0;35m7\x1b[0m", "7"
            ).replace("\x1b[0;35m4\x1b[0m",
                      "4").replace("\x1b[0;35m1\x1b[0m",
                                   "1").replace("\x1b[0;41m", "\x1b[41m"
                                               ).replace("\x1b[41m\x1b[0m", "")
            self.assertEqual(cov_show_slow_color_txt, output)

    def test_cov_fill_buffer(self):
        lines = {1: "Hello World!\n", 2: "Goodbye;\n"}
        buffer = defaultdict(list)

        buffer = cov_fill_buffer(
            end_line=1, end_column=6, count=0, lines=lines, buffer=buffer
        )
        self.assertEqual(buffer, {1: [(0, "Hello")]})
        self.assertEqual((1, 6), get_next_line_and_column(lines, buffer))
        buffer = cov_fill_buffer(
            end_line=1, end_column=14, count=1, lines=lines, buffer=buffer
        )
        self.assertEqual(buffer, {1: [(0, "Hello"), (1, " World!\n")]})
        self.assertEqual((2, 1), get_next_line_and_column(lines, buffer))
        buffer = cov_fill_buffer(
            end_line=2, end_column=10, count=42, lines=lines, buffer=buffer
        )
        self.assertEqual(
            buffer, {
                1: [(0, "Hello"), (1, " World!\n")],
                2: [(42, "Goodbye;\n")]
            }
        )
        self.assertEqual((2, 9), get_next_line_and_column(lines, buffer))

        buffer = defaultdict(list)
        buffer = cov_fill_buffer(
            end_line=2, end_column=10, count=None, lines=lines, buffer=buffer
        )
        self.assertEqual(
            buffer, {
                1: [(None, "Hello World!\n")],
                2: [(None, "Goodbye;\n")]
            }
        )
        self.assertEqual((2, 9), get_next_line_and_column(lines, buffer))
