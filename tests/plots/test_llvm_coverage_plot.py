import unittest
from unittest.mock import create_autospec

from tests.helper_utils import run_in_test_environment, UnitTestFixtures
from varats.data.reports.llvm_coverage_report import (
    CodeRegion,
    CodeRegionKind,
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
from varats.varats.plots.llvm_coverage_plot import (
    ConfusionMatrix,
    ConfusionEntry,
    CoveragePlotGenerator,
    CoverageReports,
)
from varats.varats.plots.llvm_coverage_plot import (
    classify_feature as _classify_feature,
)
from varats.varats.plots.llvm_coverage_plot import classify_all as _classify_all
from varats.varats.plots.llvm_coverage_plot import Classification

CODE_REGION_1 = CodeRegion.from_list([9, 79, 17, 2, 4, 0, 0, 0], "main")


def setup_reports(config_name: str) -> CoverageReports:
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
        case_study, report_files
    )
    assert binary_reports_map

    reports = binary_reports_map[next(iter(binary_reports_map))]
    assert len(reports) == 4

    return CoverageReports(reports)


class TestCodeRegion(unittest.TestCase):

    def test_confusion_matrix_perfect(self):
        tp = [create_autospec(ConfusionEntry) for x in range(20)]
        tn = [create_autospec(ConfusionEntry) for x in range(10)]
        fp = []
        fn = []

        matrix = ConfusionMatrix(
            true_positive=tp,
            true_negative=tn,
            false_positive=fp,
            false_negative=fn
        )
        self.assertEqual(matrix.accuracy(), 1.0)
        self.assertEqual(matrix.precision(), 1.0)
        self.assertEqual(matrix.recall(), 1.0)

    def test_confusion_matrix_not_working(self):
        tp = []
        tn = [create_autospec(ConfusionEntry) for x in range(90)]
        fp = []
        fn = [create_autospec(ConfusionEntry) for x in range(10)]

        matrix = ConfusionMatrix(
            true_positive=tp,
            true_negative=tn,
            false_positive=fp,
            false_negative=fn
        )
        self.assertEqual(matrix.accuracy(), 0.9)
        self.assertEqual(matrix.precision(), None)
        self.assertEqual(matrix.recall(), 0.0)

    def test_classify_feature(self):
        classify_feature = lambda feature, region, threshold: _classify_feature(
            feature, region, threshold, {
                "A": "A",
                "B": "B",
                "C": "C",
                "": ""
            }
        )

        region = CodeRegion(1, 1, 1, CodeRegionKind.CODE, "test")
        region.coverage_features_set = lambda: {"A", "B"}

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "C"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        self.assertEqual(
            classify_feature("A", region, 1.0), Classification.TRUE_POSITIVE
        )
        self.assertEqual(
            classify_feature("A", region, 0.0), Classification.TRUE_POSITIVE
        )
        self.assertEqual(
            classify_feature("B", region, 1.0), Classification.FALSE_NEGATIVE
        )
        self.assertEqual(
            classify_feature("B", region, 0.5), Classification.TRUE_POSITIVE
        )
        self.assertEqual(
            classify_feature("C", region, 1.0), Classification.TRUE_NEGATIVE
        )
        self.assertEqual(
            classify_feature("C", region, 0.5), Classification.FALSE_POSITIVE
        )
        self.assertEqual(
            classify_feature("", region, 1.0), Classification.TRUE_NEGATIVE
        )
        self.assertEqual(
            classify_feature("", region, 0.0001), Classification.TRUE_NEGATIVE
        )
        self.assertEqual(
            classify_feature("", region, 0.0), Classification.FALSE_POSITIVE
        )

    def test_classify_all(self):
        classify_all = lambda region, threshold: _classify_all(
            region, threshold, {
                "A": "A",
                "B": "B",
            }
        )

        region = CodeRegion(1, 1, 1, CodeRegionKind.CODE, "test")
        region.coverage_features_set = lambda: {"A", "B"}

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        # Coverage: A,B == VaRA: A,B

        self.assertEqual(
            classify_all(region, 1.0), Classification.TRUE_POSITIVE
        )

        instr_1 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A", "B"], 42, "test_instr"
        )
        instr_2 = VaraInstr(
            FeatureKind.FEATURE_REGION, "", 1, 1, ["A"], 42, "test_instr"
        )

        region.vara_instrs = [instr_1, instr_2]

        # Coverage: A,B == VaRA: A,(B)

        self.assertEqual(
            classify_all(region, 1.0), Classification.FALSE_NEGATIVE
        )
        self.assertEqual(
            classify_all(region, 0.5), Classification.TRUE_POSITIVE
        )

        region.coverage_features_set = lambda: {"A"}

        # Coverage: A == VaRA: A,(B)

        self.assertEqual(
            classify_all(region, 1.0), Classification.FALSE_NEGATIVE
        )

        self.assertEqual(
            classify_all(region, 0.0), Classification.FALSE_POSITIVE
        )

        instr_3 = VaraInstr(
            FeatureKind.NORMAL_REGION, "", 1, 1, [], 42, "test_instr"
        )
        region.vara_instrs = [instr_3]

        # Coverage: A == VaRA:

        self.assertEqual(
            classify_all(region, 1.0), Classification.FALSE_NEGATIVE
        )
        self.assertEqual(
            classify_all(region, 0.0), Classification.FALSE_NEGATIVE
        )

        region.vara_instrs = [instr_2, instr_3]
        region.coverage_features_set = lambda: {}

        # Coverage:  == VaRA: (A)

        self.assertEqual(
            classify_all(region, 0.0), Classification.FALSE_POSITIVE
        )

        self.assertEqual(
            classify_all(region, 1.0), Classification.TRUE_NEGATIVE
        )

        region.vara_instrs = []

        # Coverage:  == VaRA:

        self.assertEqual(
            classify_all(region, 1.0), Classification.TRUE_NEGATIVE
        )

        self.assertEqual(
            classify_all(region, 0.0), Classification.TRUE_NEGATIVE
        )

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_feature_report_interactions(self):
        reports = setup_reports("test_coverage_SimpleFeatureInteraction")
        report = reports.feature_report()

        # Only feature interactions should be annotated
        for func, code_region in report.filename_function_mapping[
            "src/SimpleFeatureInteraction/SFImain.cpp"].items():
            print(func)
            if func == "_Z10addPadding11PackageData":
                for region in code_region.iter_preorder():
                    self.assertEqual(
                        region.coverage_features(), "+(enc & ~compress)"
                    )
            elif func == "_Z8compress11PackageData":
                for region in code_region.iter_preorder():
                    self.assertEqual(region.coverage_features(), "+compress")
            elif func == "_Z7encrypt11PackageData":
                for region in code_region.iter_preorder():
                    self.assertEqual(region.coverage_features(), "+enc")
            elif func == "_Z18loadConfigFromArgviPPc":
                pass
            elif func == "_Z11sendPackage11PackageData":
                for region in code_region.iter_preorder():
                    if (region.start.line == 56 and
                        region.start.column == 28) or (
                            region.start.line == 56 and
                            region.start.column == 29
                        ):
                        self.assertEqual(
                            region.coverage_features(), "+(enc & ~compress)"
                        )
            else:
                for region in code_region.iter_preorder():
                    if region.coverage_features() != "":
                        pass
                    self.assertIn(region.coverage_features(), ["", "+True"])

    @run_in_test_environment(
        UnitTestFixtures.PAPER_CONFIGS, UnitTestFixtures.RESULT_FILES
    )
    def test_line_feature_plot(self):
        self.maxDiff = None
        reports = setup_reports("test_coverage_MultiSharedMultipleRegions")
        initialize_projects()
        commit_hash = FullCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        with RepositoryAtCommit(
            "FeaturePerfCSCollection", commit_hash.to_short_commit_hash()
        ) as base_dir:
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
