import json
import shutil
import unittest
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from plumbum import colors, local

from tests.helper_utils import (
    run_in_test_environment,
    UnitTestFixtures,
    TEST_INPUTS_DIR,
)
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CodeRegionKind,
    RegionStart,
    RegionEnd,
    CoverageReport,
    cov_show,
    VaraInstr,
    FeatureKind,
)
from varats.data.reports.llvm_coverage_report import (
    __cov_fill_buffer as cov_fill_buffer,
)
from varats.data.reports.llvm_coverage_report import (
    __get_next_line_and_column as get_next_line_and_column,
)
from varats.projects.discover_projects import initialize_projects
from varats.utils.git_util import RepositoryAtCommit, FullCommitHash

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main",
                                     ["test.txt"])


class TestCodeRegion(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.CODE_REGION_1 = CodeRegion(
            RegionStart(line=9, column=79),
            RegionEnd(line=17, column=2),
            count=4,
            kind=CodeRegionKind.CODE,
            function="main",
            filename="test.txt"
        )
        self.CODE_REGION_2 = CodeRegion(
            RegionStart(line=9, column=80),
            RegionEnd(line=17, column=1),
            count=0,
            kind=CodeRegionKind.CODE,
            function="main",
            filename="test.txt"
        )
        self.CODE_REGION_1.insert(self.CODE_REGION_2)

        self.root = CodeRegion.from_list([0, 0, 100, 100, 5, 0, 0, 0], "main",
                                         ["test.txt"])
        self.left = CodeRegion.from_list([0, 1, 49, 100, 5, 0, 0, 0], "main",
                                         ["test.txt"])
        self.right = CodeRegion.from_list([50, 0, 100, 99, 5, 0, 0, 0], "main",
                                          ["test.txt"])
        self.left_left = CodeRegion.from_list([30, 0, 40, 100, 3, 0, 0, 0],
                                              "main", ["test.txt"])
        self.left_left_2 = CodeRegion.from_list([10, 0, 20, 100, 3, 0, 0, 0],
                                                "main", ["test.txt"])
        self.right_right = CodeRegion.from_list([60, 0, 80, 100, 2, 0, 0, 0],
                                                "main", ["test.txt"])

        self.root.insert(self.right)
        self.root.insert(self.left_left)
        self.root.insert(self.left_left_2)
        self.root.insert(self.left)
        self.root.insert(self.right_right)
        self.tree = self.root
        self.tree.left = self.left
        self.tree.right = self.right

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

    def test_not_eq_5(self):
        self.CODE_REGION_1.function = "FooBar"
        self.assertNotEqual(self.CODE_REGION_1, CODE_REGION_1)

    def test_not_eq_6(self):
        self.CODE_REGION_1.filename = "FooBar"
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
        self.assertTrue(self.CODE_REGION_2.is_subregion(self.CODE_REGION_1))

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

    def test_find_region(self):
        self.assertEqual(
            self.root.find_code_region(line=0, column=0), self.root
        )
        self.assertEqual(
            self.root.find_code_region(line=0, column=1), self.left
        )
        self.assertEqual(
            self.root.find_code_region(line=49, column=100), self.left
        )
        self.assertEqual(
            self.root.find_code_region(line=50, column=0), self.right
        )
        self.assertEqual(
            self.root.find_code_region(line=100, column=99), self.right
        )
        self.assertEqual(
            self.root.find_code_region(line=100, column=100), self.root
        )
        self.assertEqual(
            self.root.find_code_region(line=10, column=0), self.left_left_2
        )

    def test_feature_threshold(self):
        self.root.vara_instrs.append(
            VaraInstr(
                FeatureKind.FEATURE_REGION, Path(""), 1, 1, ["A"], 42, "test"
            )
        )

        self.assertEqual(self.root.features_threshold(["A"]), 1.0)
        self.assertEqual(self.root.features_threshold(["B"]), 0.0)

    def test_coverage_json_parsing(self):
        """Parse the json export obtained from the
        https://clang.llvm.org/docs/SourceBasedCodeCoverage.html code
        example."""

        with TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            json_file = tmp_dir / "coverage.json"
            # create foo.cc file
            with open(tmp_dir / "foo.cc", "w") as foo:
                foo.write(
                    """#define BAR(x) ((x) || (x))
template <typename T> void foo(T x) {
  for (unsigned I = 0; I < 10; ++I) { BAR(I); }
}
int main() {
  foo<int>(0);
  foo<float>(0);
  return 0;
}
"""
                )
            # generate json export
            with local.cwd(tmpdir):
                local["clang++"](
                    "-O0",
                    "-g",
                    "-fprofile-instr-generate",
                    "-fcoverage-mapping",
                    "foo.cc",
                    "-o",
                    "foo",
                )
                local["chmod"]("ugo+x", "foo")
                run = local["./foo"]
                run.with_env(LLVM_PROFILE_FILE="foo.profraw")()
                local["llvm-profdata"](
                    "merge", "foo.profraw", "-o", "foo.profdata"
                )
                export = local["llvm-cov"]
                export = export["export", "./foo",
                                "-instr-profile=foo.profdata"]
                (export > str(json_file))()

            # Add absolute path to json
            with open(json_file) as file:
                coverage = json.load(file)

            coverage["absolute_path"] = str(tmp_dir.resolve())

            with open(json_file, "w") as file:
                json.dump(coverage, file)

            report = CoverageReport.from_json(json_file, base_dir=tmpdir)
        code_region = report.tree["foo.cc"]
        for region in code_region.iter_preorder():
            print(region.count)
        pass

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_cov_show(self):
        self.maxDiff = None
        initialize_projects()
        commit_hash = FullCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        with RepositoryAtCommit(
            "FeaturePerfCSCollection", commit_hash.to_short_commit_hash()
        ) as base_dir:

            with TemporaryDirectory() as tmpdir:
                shutil.unpack_archive(
                    Path(TEST_INPUTS_DIR) / "results" /
                    "FeaturePerfCSCollection" /
                    "GenCov-CovR-FeaturePerfCSCollection-MultiSharedMultipleRegions-27f1708037"
                    /
                    "2123fe9e-f47c-498e-9953-44b0fa9ad954_config-0_success.zip",
                    tmpdir
                )

                for file in Path(tmpdir).iterdir():
                    if file.suffix == ".json":
                        json_file = file

                assert json_file

                slow_report = CoverageReport.from_json(json_file, base_dir)

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

            self.assertEqual(cov_show_slow_txt, cov_show(slow_report, base_dir))
            color_state = colors.use_color
            try:
                colors.use_color = True
                output = cov_show(slow_report, base_dir)
            finally:
                colors.use_color = color_state
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

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_vara_feature_export(self):
        initialize_projects()
        commit_hash = FullCommitHash("4300ea495e7f013f68e785fdde5c4ead81297999")
        with RepositoryAtCommit(
            "FeaturePerfCSCollection", commit_hash.to_short_commit_hash()
        ) as base_dir:

            report = CoverageReport.from_report(
                Path(TEST_INPUTS_DIR) / "results" / "FeaturePerfCSCollection" /
                "GenCov-CovR-FeaturePerfCSCollection-SimpleFeatureInteraction-4300ea495e"
                / "ee663144-d5ed-469f-8caf-b211c61e9d41_config-0_success.zip",
                None, base_dir
            )

            code_region = report.tree["src/SimpleFeatureInteraction/SFImain.cpp"
                                     ]
            for region in code_region.iter_preorder():
                func = region.function
                if func == "_Z11sendPackage11PackageData":
                    if region.start.line == 51 and region.start.column == 36:
                        self.assertEqual(region.vara_features(), set())
                    elif region.start.line == 52 and region.start.column == 7:
                        self.assertEqual(region.vara_features(), set())
                    elif region.start.line == 52 and region.start.column == 22:
                        self.assertEqual(region.vara_instrs, [])
                    elif region.start.line == 52 and region.start.column == 23:
                        self.assertEqual(
                            region.vara_features(), {"Compression"}
                        )
                        self.assertEqual(
                            region.features_threshold(["Compression"]), 1.0
                        )
                    elif region.start.line == 55 and region.start.column == 7:
                        self.assertEqual(region.vara_features(), set())
                    elif region.start.line == 55 and region.start.column == 21:
                        self.assertEqual(region.vara_instrs, [])
                    elif region.start.line == 55 and region.start.column == 22:
                        self.assertEqual(region.vara_features(), {"Encryption"})
                        self.assertEqual(
                            region.features_threshold(["Encryption"]), 1.0
                        )
                    elif region.start.line == 56 and region.start.column == 9:
                        self.assertEqual(region.vara_features(), {"Encryption"})
                        self.assertEqual(
                            region.features_threshold(["Encryption"]), 1.0
                        )
                    elif region.start.line == 56 and region.start.column == 28:
                        self.assertEqual(region.vara_instrs, [])
                    elif region.start.line == 56 and region.start.column == 29:
                        self.assertEqual(
                            region.vara_features(),
                            {"Encryption", "Compression"}
                        )
                        self.assertEqual(
                            region.features_threshold(["Encryption"]), 1.0
                        )
                        self.assertEqual(
                            region.features_threshold(["Compression"]), 1.0
                        )
                        self.assertEqual(
                            region.features_threshold([
                                "Encryption", "Compression"
                            ]), 1.0
                        )

                    elif region.start.line == 59 and region.start.column == 1:
                        self.assertEqual(region.vara_instrs, [])
                    elif region.start.line == 62 and region.start.column == 1:
                        self.assertEqual(region.vara_instrs, [])
                    elif region.start.line == 66 and region.start.column == 1:
                        self.assertEqual(region.vara_instrs, [])
                    else:
                        self.fail()
                else:
                    self.assertTrue(
                        all(
                            map(
                                lambda instr: instr.kind == FeatureKind.
                                NORMAL_REGION, region.vara_instrs
                            )
                        )
                    )

    def test_cov_fill_buffer(self):
        lines = {1: "Hello World!\n", 2: "Goodbye;\n"}
        buffer = defaultdict(list)

        buffer = cov_fill_buffer(
            end_line=1,
            end_column=6,
            count=0,
            cov_features=None,
            vara_features=None,
            lines=lines,
            buffer=buffer
        )
        self.assertEqual(buffer, {1: [(0, "Hello", None, None)]})
        self.assertEqual((1, 6), get_next_line_and_column(lines, buffer))
        buffer = cov_fill_buffer(
            end_line=1,
            end_column=14,
            count=1,
            cov_features=None,
            vara_features=None,
            lines=lines,
            buffer=buffer
        )
        self.assertEqual(
            buffer,
            {1: [(0, "Hello", None, None), (1, " World!\n", None, None)]}
        )
        self.assertEqual((2, 1), get_next_line_and_column(lines, buffer))
        buffer = cov_fill_buffer(
            end_line=2,
            end_column=10,
            count=42,
            cov_features=None,
            vara_features=None,
            lines=lines,
            buffer=buffer
        )
        self.assertEqual(
            buffer, {
                1: [(0, "Hello", None, None), (1, " World!\n", None, None)],
                2: [(42, "Goodbye;\n", None, None)]
            }
        )
        self.assertEqual((2, 9), get_next_line_and_column(lines, buffer))

        buffer = defaultdict(list)
        buffer = cov_fill_buffer(
            end_line=2,
            end_column=10,
            count=None,
            cov_features=["Foo"],
            vara_features={"Bar"},
            lines=lines,
            buffer=buffer
        )
        self.assertEqual(
            buffer, {
                1: [(None, "Hello World!\n", ["Foo"], {"Bar"})],
                2: [(None, "Goodbye;\n", ["Foo"], {"Bar"})]
            }
        )
        self.assertEqual((2, 9), get_next_line_and_column(lines, buffer))
