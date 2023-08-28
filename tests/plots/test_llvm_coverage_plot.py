import typing as tp
import unittest
from unittest.mock import create_autospec

from pyeda.inter import expr

from tests.helper_utils import run_in_test_environment, UnitTestFixtures
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CodeRegionKind,
    RegionEnd,
    RegionStart,
    VaraInstr,
    FeatureKind,
    CoverageReport,
    cov_show_segment_buffer,
)
from varats.experiments.vara.llvm_coverage_experiment import (
    GenerateCoverageExperiment,
)
from varats.paper.paper_config import get_loaded_paper_config, load_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.plot.plots import PlotConfig
from varats.projects.discover_projects import initialize_projects
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import RepositoryAtCommit, FullCommitHash
from varats.utils.settings import save_config, vara_cfg
from varats.varats.data.reports.llvm_coverage_report import (
    minimize,
    expr_to_str,
)
from varats.varats.plots.llvm_coverage_plot import (
    CoveragePlotGenerator,
    CoverageReports,
    coverage_found_features,
    ConfusionMatrix,
    _matrix_analyze_code_region,
)
from varats.varats.plots.llvm_coverage_plot import (
    vara_found_features as _vara_found_features,
)

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main",
                                     ["test.txt"])


def _confusion_matrix(
    feature: tp.Optional[str], tree: CodeRegion,
    feature_name_map: tp.Dict[str, str], threshold: float, file: str
) -> ConfusionMatrix:
    coverage_feature_regions = []
    coverage_normal_regions = []
    vara_feature_regions = []
    vara_normal_regions = []

    _matrix_analyze_code_region(
        feature, tree, feature_name_map, threshold, file,
        coverage_feature_regions, coverage_normal_regions, vara_feature_regions,
        vara_normal_regions
    )

    return ConfusionMatrix(
        actual_positive_values=coverage_feature_regions,
        actual_negative_values=coverage_normal_regions,
        predicted_positive_values=vara_feature_regions,
        predicted_negative_values=vara_normal_regions
    )


def setup_reports(config_name: str, base_dir: str) -> CoverageReports:
    # setup config
    vara_cfg()['paper_config']['current_config'] = config_name
    load_paper_config()
    save_config()

    plot_generator = CoveragePlotGenerator(
        PlotConfig.from_kwargs(view=False),
        experiment_type=[GenerateCoverageExperiment],
        case_study=get_loaded_paper_config().
        get_case_studies("FeaturePerfCSCollection")
    )
    plots = plot_generator.generate()
    assert len(plots) == 1
    coverage_plot = plots[0]

    case_studies = get_loaded_paper_config().get_all_case_studies()
    assert len(case_studies) == 1
    case_study = case_studies[0]

    project_name = case_study.project_name

    report_files = get_processed_revisions_files(
        project_name,
        GenerateCoverageExperiment,
        CoverageReport,
        get_case_study_file_name_filter(case_study),
        only_newest=False,
    )

    binary_reports_map = coverage_plot._get_binary_reports_map(
        case_study, report_files, base_dir
    )
    assert binary_reports_map

    reports = binary_reports_map[next(iter(binary_reports_map))]
    assert len(reports) == 4

    return CoverageReports(reports)


class TestCoveragePlot(unittest.TestCase):

    def test_coverage_found_features(self):
        region = create_autospec(CodeRegion)
        region.coverage_features_set = lambda: set(["A", "B"])

        self.assertTrue(coverage_found_features(set(["A", "B"]), region))
        self.assertFalse(coverage_found_features(set(["A", "B", "C"]), region))

        self.assertTrue(coverage_found_features(set(["A"]), region))
        self.assertFalse(coverage_found_features(set(), region))

    def test_vara_found_features(self):
        vara_found_features = lambda feature, region, threshold: _vara_found_features(
            feature, region, threshold, {
                "a": {"A"},
                "b": {"B"},
                "c": {"C"},
                "": {""}
            }
        )

        region = CodeRegion(1, 1, 1, CodeRegionKind.CODE, "test", "test.txt")

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "C"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        self.assertTrue(vara_found_features(set(["a", "b"]), region, 0.0))
        self.assertTrue(vara_found_features(set(["a", "b"]), region, 0.5))
        self.assertFalse(vara_found_features(set(["a", "b"]), region, 1.0))

        self.assertFalse(vara_found_features(set(["a", "b", "c"]), region, 0.0))

        self.assertFalse(vara_found_features(set(["b"]), region, 1.0))
        self.assertTrue(vara_found_features(set(["b"]), region, 0.5))
        self.assertTrue(vara_found_features(set(["b"]), region, 0))

        self.assertFalse(vara_found_features(set(["c"]), region, 1.0))
        self.assertTrue(vara_found_features(set(["c"]), region, 0.5))
        self.assertTrue(vara_found_features(set(["c"]), region, 0))

        self.assertTrue(vara_found_features(set(["a"]), region, 1.0))
        self.assertFalse(vara_found_features(set([""]), region, 0.0))
        self.assertFalse(vara_found_features(set(), region, 0.0))

        with self.assertRaises(ValueError):
            vara_found_features(set(), region, threshold=100)

        with self.assertRaises(KeyError):
            self.assertFalse(vara_found_features(set(["d"]), region, 0.0))

    def test_confusion_matrix_single_feature(self):

        def confusion_matrix(
            feature: tp.Optional[str],
            tree: CodeRegion,
            threshold: float,
        ) -> ConfusionMatrix:
            return _confusion_matrix(
                feature, tree, {
                    "A": {"A"},
                    "B": {"B"},
                    "C": {"C"},
                    "": {""}
                }, threshold, "test"
            )

        region = CodeRegion(
            RegionStart(1, 1), RegionEnd(1, 1), 1, CodeRegionKind.CODE, "test",
            "test.txt"
        )
        region.coverage_features_set = lambda: {"A", "B"}

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "C"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        self.assertEqual(confusion_matrix("A", region, 1.0).TP, 1)
        self.assertEqual(confusion_matrix("A", region, 0.0).TP, 1)

        self.assertEqual(confusion_matrix("B", region, 1.0).FN, 1)
        self.assertEqual(confusion_matrix("B", region, 0.5).TP, 1)

        self.assertEqual(confusion_matrix("C", region, 1.0).TN, 1)
        self.assertEqual(confusion_matrix("C", region, 0.5).FP, 1)

        self.assertEqual(confusion_matrix("", region, 1.0).TN, 1)
        self.assertEqual(confusion_matrix("", region, 0.0).TN, 1)

    def test_confusion_matrix_all_features(self):

        def confusion_matrix(
            tree: CodeRegion,
            threshold: float,
        ) -> ConfusionMatrix:
            return _confusion_matrix(
                None, tree, {
                    "a": {"A"},
                    "b": {"B"},
                    "A": {"a"},
                    "B": {"b"},
                }, threshold, "test"
            )

        region = CodeRegion(
            RegionStart(1, 1), RegionEnd(1, 1), 1, CodeRegionKind.CODE, "test",
            "test.txt"
        )
        region.coverage_features_set = lambda: {"a", "b"}

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        # Coverage: A,B == VaRA: A,B
        self.assertEqual(confusion_matrix(region, 1.0).TP, 1)

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        # Coverage: A,B == VaRA: A,(B)

        self.assertEqual(confusion_matrix(region, 1.0).FN, 1)
        self.assertEqual(confusion_matrix(region, 0.5).TP, 1)

        region.coverage_features_set = lambda: {"a"}

        # Coverage: A == VaRA: A,(B)
        self.assertEqual(confusion_matrix(region, 1.0).TP, 1)
        self.assertEqual(confusion_matrix(region, 0.5).FP, 1)
        self.assertEqual(confusion_matrix(region, 0.0).FP, 1)

        instr_3 = VaraInstr(
            FeatureKind.NORMAL_REGION, "", 1, 1, [], 42, "test_instr"
        )
        region.vara_instrs = [instr_3]

        # Coverage: A == VaRA:

        self.assertEqual(confusion_matrix(region, 1.0).FN, 1)
        self.assertEqual(confusion_matrix(region, 0.0).FN, 1)

        region.vara_instrs = [instr_2, instr_3]
        region.coverage_features_set = lambda: set()

        # Coverage:  == VaRA: (A)

        self.assertEqual(confusion_matrix(region, 1.0).TN, 1)
        self.assertEqual(confusion_matrix(region, 0.0).FP, 1)

        region.vara_instrs = []

        # Coverage:  == VaRA:

        self.assertEqual(confusion_matrix(region, 1.0).TN, 1)
        self.assertEqual(confusion_matrix(region, 0.0).TN, 1)

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_feature_report_interactions(self):
        initialize_projects()
        commit_hash = FullCommitHash("4300ea495e7f013f68e785fdde5c4ead81297999")
        with RepositoryAtCommit(
            "FeaturePerfCSCollection", commit_hash.to_short_commit_hash()
        ) as base_dir:
            reports = setup_reports(
                "test_coverage_SimpleFeatureInteraction", base_dir
            )
            report = reports.feature_report()

            code_region = report.tree["src/SimpleFeatureInteraction/SFImain.cpp"
                                     ]
            # Only feature interactions should be annotated
            for region in code_region.iter_preorder():
                func = region.function
                print(func)
                if func == "_Z10addPadding11PackageData":
                    self.assertEqual(
                        region.coverage_features(), "+(enc & ~compress)"
                    )
                elif func == "_Z8compress11PackageData":
                    self.assertEqual(region.coverage_features(), "+compress")
                elif func == "_Z7encrypt11PackageData":
                    self.assertEqual(region.coverage_features(), "+enc")
                elif func == "_Z18loadConfigFromArgviPPc":
                    pass
                elif func == "_Z11sendPackage11PackageData":
                    if region.kind == CodeRegionKind.GAP:
                        # GAP Regions. Are covered, but don't have instructions associated.
                        # Therefore we do not annotate presence conditions to them.
                        self.assertEqual(len(region.vara_instrs), 0)
                        self.assertEqual(len(region.presence_conditions), 0)

                    if region.start.line == 56 and region.start.column == 29:
                        self.assertEqual(
                            region.coverage_features(), "+(enc & ~compress)"
                        )
                else:
                    if region.coverage_features() != "":
                        pass
                    self.assertIn(region.coverage_features(), ["", "+True"])

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_line_feature_plot(self):
        self.maxDiff = None
        initialize_projects()
        commit_hash = FullCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        with RepositoryAtCommit(
            "FeaturePerfCSCollection", commit_hash.to_short_commit_hash()
        ) as base_dir:
            reports = setup_reports(
                "test_coverage_MultiSharedMultipleRegions", base_dir
            )
            #feature_model = expr(
            #    "(slow & header) | (~slow & header) | (slow & ~header) | (~slow & ~header)"
            #)
            #reports._feature_model = expr(True)
            #self.assertEqual(reports.feature_model(), feature_model)

            self.assertEqual(
                """include/fpcsc/perf_util/feature_cmd.h:
    1|#ifndef FPCSC_PERFUTIL_FEATURECMD_H                                             |
    2|#define FPCSC_PERFUTIL_FEATURECMD_H                                             |
    3|                                                                                |
    4|#include <exception>                                                            |
    5|#include <stdlib.h>                                                             |
    6|#include <string>                                                               |
    7|                                                                                |
    8|namespace fpcsc {                                                               |
    9|inline bool isFeatureEnabled(int argc, char *argv[], std::string FeatureName) { |+True
   10|  for (int CurrentArg = 1; CurrentArg < argc; ++CurrentArg) {                   |+(header | slow), +True
   11|    if (argv[CurrentArg] == FeatureName) {                                      |+(header | slow)
   12|      return true;                                                              |+(header | slow)
   13|    }                                                                           |+(header | slow)
   14|  }                                                                             |+(header | slow)
   15|                                                                                |
   16|  return false;                                                                 |+True
   17|}                                                                               |+True
   18|                                                                                |
   19|inline long getFeatureValue(int argc, char *argv[], std::string FeatureName) {  |
   20|  int CurrentArg = 1;                                                           |
   21|  for (; CurrentArg < argc; ++CurrentArg) {                                     |
   22|    if (argv[CurrentArg] == FeatureName) {                                      |
   23|      ++CurrentArg;                                                             |
   24|      break;                                                                    |
   25|    }                                                                           |
   26|  }                                                                             |
   27|                                                                                |
   28|  if (CurrentArg >= argc) {                                                     |
   29|    return 0;                                                                   |
   30|  }                                                                             |
   31|                                                                                |
   32|  return strtol(argv[CurrentArg], NULL, 0);                                     |
   33|}                                                                               |
   34|                                                                                |
   35|} // namespace fpcsc                                                            |
   36|                                                                                |
   37|#endif // FPCSC_PERFUTIL_FEATURECMD_H                                           |

include/fpcsc/perf_util/sleep.h:
    1|#ifndef FPCSC_PERFUTIL_SLEEP_H                                                  |
    2|#define FPCSC_PERFUTIL_SLEEP_H                                                  |
    3|                                                                                |
    4|#include <chrono>                                                               |
    5|#include <iostream>                                                             |
    6|#include <thread>                                                               |
    7|                                                                                |
    8|namespace fpcsc {                                                               |
    9|                                                                                |
   10|inline void sleep_for_secs(unsigned Secs) {                                     |+True
   11|  std::cout << "Sleeping for " << Secs << " seconds" << std::endl;              |+True
   12|  std::this_thread::sleep_for(std::chrono::seconds(Secs));                      |+True
   13|}                                                                               |+True
   14|                                                                                |
   15|inline void sleep_for_millisecs(unsigned Millisecs) {                           |
   16|  std::cout << "Sleeping for " << Millisecs << " milliseconds" << std::endl;    |
   17|  std::this_thread::sleep_for(std::chrono::milliseconds(Millisecs));            |
   18|}                                                                               |
   19|                                                                                |
   20|inline void sleep_for_nanosecs(unsigned millisecs) {                            |
   21|  std::this_thread::sleep_for(std::chrono::nanoseconds(millisecs));             |
   22|}                                                                               |
   23|                                                                                |
   24|} // namespace fpcsc                                                            |
   25|                                                                                |
   26|#endif // FPCSC_PERFUTIL_SLEEP_H                                                |

src/MultiSharedMultipleRegions/FeatureHeader.cpp:
    1|#include "FeatureHeader.h"                                                      |
    2|                                                                                |
    3|bool ExternFeature = false;                                                     |
    4|                                                                                |
    5|static bool CppFeature = false;                                                 |
    6|                                                                                |
    7|void enableCppFeature() {                                                       |
    8|  CppFeature = true;                                                            |
    9|}                                                                               |
   10|                                                                                |
   11|bool isCppFeatureEnabled() {                                                    |+True
   12|  return CppFeature;                                                            |+True
   13|}                                                                               |+True

src/MultiSharedMultipleRegions/FeatureHeader.h:
    1|#ifndef FEATURE_HEADER_H                                                        |
    2|#define FEATURE_HEADER_H                                                        |
    3|                                                                                |
    4|extern bool ExternFeature;                                                      |
    5|                                                                                |
    6|static inline bool HeaderFeature = false;                                       |
    7|                                                                                |
    8|inline void enableExternFeature() {                                             |
    9|  ExternFeature = true;                                                         |
   10|}                                                                               |
   11|                                                                                |
   12|void enableCppFeature();                                                        |
   13|bool isCppFeatureEnabled();                                                     |
   14|                                                                                |
   15|#endif // FEATURE_HEADER_H                                                      |

src/MultiSharedMultipleRegions/MSMRmain.cpp:
    1|#include "FeatureHeader.h"                                                      |
    2|                                                                                |
    3|#include "fpcsc/perf_util/sleep.h"                                              |
    4|#include "fpcsc/perf_util/feature_cmd.h"                                        |
    5|                                                                                |
    6|#include <string>                                                               |
    7|                                                                                |
    8|int main(int argc, char *argv[] ) {                                             |+True
    9|  bool Slow = false;                                                            |+True
   10|                                                                                |
   11|  if (fpcsc::isFeatureEnabled(argc, argv, std::string("--slow"))) {             |+True, +slow
   12|    Slow = true;                                                                |+slow
   13|  }                                                                             |+slow
   14|                                                                                |
   15|  if (fpcsc::isFeatureEnabled(argc, argv, std::string("--header"))) {           |+True, +header
   16|    HeaderFeature = true;                                                       |+header
   17|  }                                                                             |+header
   18|                                                                                |
   19|  if (fpcsc::isFeatureEnabled(argc, argv, std::string("--extern"))) {           |+True
   20|    enableExternFeature();                                                      |
   21|  }                                                                             |
   22|                                                                                |
   23|  if (fpcsc::isFeatureEnabled(argc, argv, std::string("--cpp"))) {              |+True
   24|    enableCppFeature();                                                         |
   25|  }                                                                             |
   26|                                                                                |
   27|  // Multiple regions related to --slow that take different amounts of time.    |
   28|                                                                                |
   29|  if (Slow) {                                                                   |+True, +slow
   30|    fpcsc::sleep_for_secs(5);                                                   |+slow
   31|  } else {                                                                      |+slow, +~slow
   32|    fpcsc::sleep_for_secs(3);                                                   |+~slow
   33|  }                                                                             |+~slow
   34|                                                                                |
   35|  fpcsc::sleep_for_secs(2); // General waiting time                             |+True
   36|                                                                                |
   37|  if (HeaderFeature) {                                                          |+True, +header
   38|    fpcsc::sleep_for_secs(3);                                                   |+header
   39|  } else {                                                                      |+header, +~header
   40|    fpcsc::sleep_for_secs(1);                                                   |+~header
   41|  }                                                                             |+~header
   42|                                                                                |
   43|  fpcsc::sleep_for_secs(2); // General waiting time                             |+True
   44|                                                                                |
   45|  if (ExternFeature) {                                                          |+True
   46|    fpcsc::sleep_for_secs(6);                                                   |
   47|  }                                                                             |
   48|                                                                                |
   49|  fpcsc::sleep_for_secs(2); // General waiting time                             |+True
   50|                                                                                |
   51|  if (isCppFeatureEnabled()) {                                                  |+True
   52|    fpcsc::sleep_for_secs(3);                                                   |
   53|  }                                                                             |
   54|                                                                                |
   55|  return 0;                                                                     |+True
   56|}                                                                               |+True

""",
                cov_show_segment_buffer(
                    reports.feature_segments(base_dir),
                    show_counts=False,
                    show_coverage_features=True
                )
            )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_confusion_matrices(self):
        initialize_projects()
        commit_hash = FullCommitHash("4300ea495e7f013f68e785fdde5c4ead81297999")
        with RepositoryAtCommit(
            "FeaturePerfCSCollection", commit_hash.to_short_commit_hash()
        ) as base_dir:
            reports = setup_reports(
                "test_coverage_SimpleFeatureInteraction", base_dir
            )
            feature_option_mapping = reports.feature_option_mapping(
                additional_info={
                    "root": "",
                    "Compression": "--compress",
                    "Encryption": "--enc",
                    "Slow": "--slow"
                }
            )
            result_1 = reports.confusion_matrices(
                feature_option_mapping, threshold=1.0
            )
            result_0 = reports.confusion_matrices(
                feature_option_mapping, threshold=0.0
            )

            for result in [result_1, result_0]:
                print(result)
                enc = result["enc"]
                self.assertEqual(enc.TP, 3)
                self.assertEqual(enc.TN, 39)
                self.assertEqual(enc.FP, 0)
                self.assertEqual(enc.FN, 8)

                compress = result["compress"]
                self.assertEqual(compress.TP, 2)
                self.assertEqual(compress.TN, 40)
                self.assertEqual(compress.FP, 0)
                self.assertEqual(compress.FN, 8)

                all = result["__all__"]
                self.assertEqual(all.TP, 4)
                self.assertEqual(all.TN, 36)
                self.assertEqual(all.FP, 0)
                self.assertEqual(all.FN, 10)

    def test_presence_condition_simplification_1(self):
        feature_model = expr(
            "(~compress & enc) | (compress & ~enc) | (compress & enc)"
        )
        expression = expr(
            "(~compress & enc) | (compress & ~enc) | (compress & enc)"
        )
        self.assertEqual(minimize(expression, feature_model), expr(True))
        expression = expr("(compress & enc)")
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "(compress & enc)"
        )

    def test_presence_condition_simplification_2(self):
        feature_model = expr(
            "(~compress & ~enc) | (~compress & enc) | (compress & ~enc) | (compress & enc)"
        )
        expression = expr(
            "(~compress & enc) | (compress & ~enc) | (compress & enc)"
        )
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "(compress | enc)"
        )
        feature_model = expr(True)
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "(compress | enc)"
        )

    def test_presence_condition_simplification_3(self):
        feature_model = expr(False)
        expression = expr(
            "(~compress & enc) | (compress & ~enc) | (compress & enc)"
        )
        self.assertEqual(minimize(expression, feature_model), expr(False))
        expression = expr(False)
        self.assertEqual(minimize(expression, feature_model), expr(False))
        expression = expr(True)
        self.assertEqual(minimize(expression, feature_model), expr(True))

    def test_presence_condition_simplification_4(self):
        feature_model = None
        expression = expr(
            "(~compress & enc) | (compress & ~enc) | (compress & enc)"
        )
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "(compress | enc)"
        )
        expression = expr(False)
        self.assertEqual(minimize(expression, feature_model), expr(False))
        expression = expr(True)
        self.assertEqual(minimize(expression, feature_model), expr(True))

    def test_presence_condition_simplification_5(self):
        feature_model = expr(
            "((compress & enc) | (compress & ~enc) | (enc & ~compress) | (~compress & ~enc))"
        )
        expression = ((((expr(True) & expr("enc")) & expr("compress")) |
                       expr(False)) |
                      ((expr(True) & expr("compress") & expr("~enc"))))
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "compress"
        )

    def test_presence_condition_simplification_6(self):
        feature_model = expr(
            "(slow & header) | (~slow & header) | (slow & ~header) | (~slow & ~header)"
        )
        expression = expr("(slow & header) | (slow & ~header)")
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "slow"
        )
        feature_model = expr(True)
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "slow"
        )
        feature_model = expr(
            "(header & slow) | (~header & slow) | (header & ~slow) | (~header & ~slow)"
        )
        expression = expr("(header & slow) | (~header & slow)")
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "slow"
        )
        feature_model = expr(True)
        self.assertEqual(
            expr_to_str(minimize(expression, feature_model)), "slow"
        )

    def test_pyeda(self):
        from pyeda.inter import (
            exprvar,
            truthtable,
            truthtable2expr,
            espresso_tts,
        )

        # Pyeda's espresso_tts implementation does not respect tt variable ordering
        a, b, c, d = map(exprvar, 'abcd')
        f_tt = truthtable((a, b, c), '10110101')
        f_ex = truthtable2expr(f_tt)
        g_ex = espresso_tts(f_tt)[0]
        self.assertTrue(f_ex.equivalent(g_ex))

        f_tt = truthtable((c, b, a), '10110101')
        f_ex = truthtable2expr(f_tt)
        g_ex = espresso_tts(f_tt)[0]
        self.assertTrue(f_ex.equivalent(g_ex))

        f_tt = truthtable((b, a, c), '10110101')
        f_ex = truthtable2expr(f_tt)
        g_ex = espresso_tts(f_tt)[0]
        self.assertTrue(f_ex.equivalent(g_ex))

        f_tt = truthtable((d, c, b, a), '1011010110010100')
        f_ex = truthtable2expr(f_tt)
        g_ex = espresso_tts(f_tt)[0]
        self.assertTrue(f_ex.equivalent(g_ex))
