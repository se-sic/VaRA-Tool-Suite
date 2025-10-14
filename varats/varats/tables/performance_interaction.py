"""Performance interaction eval."""
import ast
import logging
import typing as tp
from collections import defaultdict
from itertools import pairwise

import numpy as np
import pandas as pd

from varats.base.configuration import (
    PlainCommandlineConfiguration,
    Configuration,
)
from varats.data.databases.performance_evolution_database import (
    PerformanceEvolutionDatabase,
)
from varats.data.metrics import ConfusionMatrix
from varats.data.reports.performance_interaction_report import (
    PerformanceInteractionReport,
)
from varats.experiments.base.perf_sampling import PerfSamplingSynth
from varats.experiments.vara.performance_interaction import (
    PerformanceInteractionExperiment,
    PerformanceInteractionExperimentSynthetic,
)
from varats.jupyterhelper.file import (
    load_performance_interaction_report,
    load_mpr_wl_time_report_aggregate,
    load_mpr_performance_interaction_report,
)
from varats.mapping.commit_map import get_commit_map
from varats.mapping.configuration_map import ConfigurationMap
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config, get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.report.gnu_time_report import MPRWLTimeReportAggregate
from varats.report.report import FileStatusExtension
from varats.revision.revisions import (
    get_processed_revisions_files,
    get_files_with_status_by_config,
)
from varats.table.table import Table
from varats.table.table_utils import dataframe_to_table
from varats.table.tables import TableFormat, TableGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.utils.config import load_configuration_map_for_case_study
from varats.utils.git_util import ShortCommitHash

if tp.TYPE_CHECKING:
    from varats.data.reports.performance_interaction_report import (
        PerfInteraction,
    )

LOG = logging.Logger(__name__)

Revision = tp.Union[ShortCommitHash, str]


class FeatureLike(tp.Protocol):

    def should_include_config(
        self, config: Configuration, relevant_features: tp.Iterable[str]
    ) -> bool:
        ...


class Feature:

    def __init__(
        self,
        name: str,
        values: tp.Union[str, tp.List[str]],
    ):
        self.name = name

        self.values: tp.List[str] = []

        if isinstance(values, list):
            self.values = values
        else:
            self.values.append(values)

    def config_value(self, config: Configuration) -> tp.Optional[str]:
        for v in self.values:
            if config.get_config_value(v):
                return v

        return None


F1 = Feature("FR(F1)", "f1")
F2 = Feature("FR(F2)", "f2")
F3 = Feature("FR(F3)", "f3")
F4 = Feature("FR(F4)", "f4")
F5 = Feature("FR(F5)", "f5")
F6 = Feature("FR(F6)", "f6")
F7 = Feature("FR(F7)", "f7")
F8 = Feature("FR(F8)", "f8")
F9 = Feature("FR(F9)", "f9")
F10 = Feature("FR(F10)", "f10")

# default values for features
CONFIG_DATA: tp.Dict[str, tp.List[Feature]] = {
    "coreutils_basenc": [
        Feature("base2lsbf", "base2lsbf"),
        Feature("base2msbf", "base2msbf"),
        Feature("base16", "base16"),
        Feature("base32", "base32"),
        Feature("base32hex", "base32hex"),
        Feature("base64", "base64"),
        Feature("base64url", "base64url"),
        Feature("decode", "d"),
        Feature("ignore_garbage", "i"),
        Feature("wrap", ["wrap=0", "wrap=25", "wrap=76"]),
    ],
    "coreutils_cksum": [
        Feature("sha512", "algorithm=sha512"),
        Feature("sha256", "algorithm=sha256"),
        Feature("sha1", "algorithm=sha1"),
        Feature("crc", "algorithm=crc"),
        Feature("md5", "algorithm=md5"),
        Feature("sm3", "algorithm=sm3"),
        Feature("blake2b", "algorithm=blake2b"),
        Feature("base64", "base64"),
        Feature("raw", "raw"),
        Feature("tag", "tag"),
        Feature("untagged", "untagged"),
        Feature("length", ["length=64", "length=128", "length=256"]),
    ],
    "coreutils_dd": [
        Feature("ucase", "conv=ucase"),
        Feature("swab", "conv=swab"),
        Feature("ibm", "conv=ibm"),
        Feature("fdatasync", "conv=fdatasync"),
        Feature("ebcdic", "conv=ebcdic"),
        Feature("block", "conv=block"),
        Feature("unblock", "conv=unblock"),
        Feature("lcase", "conv=lcase"),
        Feature("fsync", "conv=fsync"),
        Feature("sync", "conv=sync"),
        Feature("sparse", "conv=sparse"),
        Feature("ascii", "conv=ascii"),
        Feature("status_none", "status=none"),
        Feature("status_noxfer", "status=noxfer"),
        Feature("status_progress", "status=progress"),
        Feature("convert_bytes", ["cbs=128", "cbs=512", "cbs=2048"]),
        Feature("input_bytes", ["ibs=128", "cbs=512", "cbs=2048"]),
        Feature("output_bytes", ["obs=128", "cbs=512", "cbs=2048"]),
    ],
    "coreutils_fmt": [
        Feature("crown_margin", "c"),
        Feature("prefix", "prefix=        <p n="),
        Feature("split_only", "s"),
        Feature("tagged_paragraph", "t"),
        Feature("uniform_spacing", "u"),
        Feature("width", "width="),
        Feature("goal", "goal="),
    ],
    "coreutils_od": [
        Feature("address_radix_d", "Ad"),
        Feature("address_radix_o", "Ao"),
        Feature("address_radix_x", "Ax"),
        Feature("address_radix_n", "An"),
        Feature("endian_big", "endian=big"),
        Feature("endian_little", "endian=little"),
        Feature("hexadecimal_trailer", "format=x2z"),
        Feature("named_character", "format=a"),
        Feature("unsigned_long", "format=uL"),
        Feature("signed_int", "format=dI"),
        Feature("octal", "format=o2"),
        Feature("float", "format=fF"),
        Feature("character", "format=c"),
        Feature("output-duplicates", "v"),
        Feature("strings", ["strings=1", "strings=3", "strings=8"]),
        Feature("width", ["width=16", "width=32", "width=64"]),
    ],
    "coreutils_pr": [
        Feature("across", "a"),
        Feature("show_control_chars", "c"),
        Feature("show_nonprinting", "v"),
        Feature("double_space", "d"),
        Feature("join_lines", "J"),
        Feature("merge", "m"),
        Feature("number_lines", "n"),
        Feature("omit_header", "t"),
        Feature("sep_string", "S"),
        Feature("columns", ["columns=1", "columns=3"]),
        Feature("length", ["length=15", "length=66"]),
        Feature("page_width", ["page_width=50", "page_width=72"]),
    ],
    "coreutils_sort": [
        Feature("numeric-sort", "n"),
        Feature("random-sort", "R"),
        Feature("version-sort", "V"),
        Feature("ignore-case", "f"),
        Feature("reverse", "r"),
        Feature("stable", "s"),
        Feature("unique", "u"),
        Feature("parallel", "parallel=4"),
    ],
    "coreutils_uniq": [
        Feature("count", "count"),
        Feature("repeated", "repeated"),
        Feature("unique", "unique"),
        Feature("ignore_case", "ignore-case"),
        Feature("all_repeated_none", "all-repeated=none"),
        Feature("all_repeated_prepend", "all-repeated=prepend"),
        Feature("all_repeated_separate", "all-repeated=separate"),
        Feature("group_separate", "group=separate"),
        Feature("group_prepend", "group=prepend"),
        Feature("group_append", "group=append"),
        Feature("group_both", "group=both"),
        Feature("check-chars", ["check-chars=8", "check-chars=16"]),
        Feature("skip-chars", ["skip-chars=8", "skip-chars=16"]),
        Feature("check-fields", ["check-fields=8"]),
    ],
    "coreutils_wc": [
        Feature("bytes", "bytes"),
        Feature("chars", "chars"),
        Feature("lines", "lines"),
        Feature("words", "words"),
        Feature("max_line_length", "max-line-length"),
    ],
    "InterStructural": [F1],
    "InterDataFlow": [F1],
    "InterImplicitFlow": [F1],
    "FunctionSingle": [F1, F2, F3],
    "FunctionAccumulating": [F1, F2, F3],
    "FunctionMultiple": [F1, F2, F3],
    "DegreeLow": [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10],
    "DegreeHigh": [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10],
    "DegreeComplex": [F1, F2, F3, F4, F5, F6, F7, F8, F9, F10],
    "bzip2": [
        Feature("forceOverwrite", "f"),
        Feature("keepInputFiles", "k"),
        Feature("compress", "z"),
        Feature("decompress", "d"),
        Feature("quiet", "q"),
        Feature("smallMode", "s"),
        Feature("stdout", "c"),
        Feature("verbosity", "v"),
        Feature("level", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]),
    ],
    "grep": [
        Feature("ignore_case", "i"),
        Feature("invert_match", "v"),
        Feature("count", "c"),
        Feature("only_matching", "o"),
        Feature("word_regex", "w"),
        Feature("line_regex", "x"),
        Feature("files_with_match", "l"),
        Feature("files_without_match", "L"),
        Feature("context_5", "C5"),
        Feature("context_10", "C10")
    ],
    "picosat": [
        Feature("Plain", "plain"),
        Feature("Partial", "partial"),
        Feature("CompactTrace", "t"),
        Feature("ExtendedTrace", "T"),
        Feature("ReverseUnitPropagationProof", "r"),
    ],
}


class EvalData(tp.TypedDict):
    """Dict representing data for a confusion matrix."""
    baseline_positives: tp.List[Revision]
    baseline_negatives: tp.List[Revision]
    rq1_predicted_positives: tp.List[Revision]
    rq1_predicted_negatives: tp.List[Revision]
    rq2_predicted_positives: tp.List[Revision]
    rq2_predicted_negatives: tp.List[Revision]


def get_performance_data(
    performance_data: pd.DataFrame, revision: Revision, config_id: int
) -> tp.List[float]:
    try:
        vals_raw = performance_data.loc[config_id, revision]
    except KeyError:
        return []

    if vals_raw is np.nan:
        return []

    if isinstance(vals_raw, list):
        return vals_raw

    return tp.cast(tp.List[float], ast.literal_eval(vals_raw))


def get_regressing_configs(
    performance_data: pd.DataFrame, old_rev: Revision, new_rev: Revision,
    configs: ConfigurationMap, threshold: float, sigma: float, min_diff: float,
    ignore_old_zero: bool
) -> ConfigurationMap:
    """Calculates the regressing configurations between two revisions."""
    regressing_configs: ConfigurationMap = ConfigurationMap()
    for cid, config in configs.id_config_tuples():
        old_vals = get_performance_data(performance_data, old_rev, cid)
        new_vals = get_performance_data(performance_data, new_rev, cid)

        if is_regression(
            old_vals, new_vals, threshold, sigma, min_diff, ignore_old_zero
        ):
            regressing_configs.add_configuration(config, config_id=cid)

    return regressing_configs


def get_num_regressions(
    performance_data: pd.DataFrame, old_rev: Revision, new_rev: Revision,
    configs: ConfigurationMap, threshold: float, sigma: float, min_diff: float,
    ignore_old_zero: bool
) -> int:
    """Calculates the number of regressing configurations between two
    revisions."""
    return len(
        get_regressing_configs(
            performance_data, old_rev, new_rev, configs, threshold, sigma,
            min_diff, ignore_old_zero
        ).ids()
    )


def is_regression(
    old_vals: list[float], new_vals: list[float], threshold: float,
    sigma: float, min_diff: float, ignore_old_zero: bool
) -> bool:
    """
    Calculates if there is a regression between two revisions.

    A regression exists if for at least one configuration the performance
    difference exceeds the `threshold` and is at least `sigma` times greater
    than the standard deviation of the performance measurements.
    Ignore regressions with a smaller absolute value than `min_diff`.

    Args:
        old_vals: old performance data
        new_vals: new performance data
        threshold: percentage change that is considered a regression
        sigma: factor that controls the minimum difference to the standard
               deviation of the measurements
        min_diff: minimum absolute difference to be considered a regression
        ignore_old_zero: if True, ignore configurations where the old revision
                         has an average 0s execution time; this can happen if
                         new configurations are introduced in the new revision

    Returns:
    """
    if not old_vals or not new_vals:
        return False

    std_old = np.std(old_vals)
    std_new = np.std(new_vals)
    std = max(std_old, std_new)

    old_avg = np.average(old_vals)
    new_avg = np.average(new_vals)
    diff = abs(old_avg - new_avg)

    if ignore_old_zero and old_avg == 0:
        return False

    if diff >= max(threshold * old_avg, sigma * std, min_diff):
        return True

    return False


def get_relevant_configs(
    project_name: str, configs: ConfigurationMap, relevant_features: tp.Set[str]
) -> ConfigurationMap:
    """
    Computes relevant configurations according to a performance interaction
    report.

    We include configurations such that they cover all possible interactions
    between relevant features.
    """
    relevant_configs: ConfigurationMap = ConfigurationMap()
    seen_tuples: tp.Set[tp.Tuple[tp.Optional[str], ...]] = set()
    features = list(
        filter(
            lambda f: f.name in relevant_features, CONFIG_DATA[project_name]
        )
    )

    def get_relevant_tuple(c: Configuration) -> tp.Tuple[tp.Optional[str], ...]:
        return tuple(f.config_value(c) for f in features)

    # collect all configs with unseen combinations of relevant features
    for config_id, config in configs.id_config_tuples():
        relevant_tuple = get_relevant_tuple(config)

        if relevant_tuple not in seen_tuples:
            seen_tuples.add(relevant_tuple)
            relevant_configs.add_configuration(config, config_id=config_id)

    return relevant_configs


def calculate_eval_data(
    project_name: str, performance_data: pd.DataFrame, old_rev: Revision,
    new_rev: Revision, configs: ConfigurationMap,
    report: tp.Optional[PerformanceInteractionReport], threshold: float,
    sigma: float, min_diff: float, ignore_old_zero: bool, eval_data: EvalData
) -> None:
    # RQ1
    regressing_configs = get_regressing_configs(
        performance_data, old_rev, new_rev, configs, threshold, sigma, min_diff,
        ignore_old_zero
    )

    is_reg = len(regressing_configs.ids()) > 0

    if is_reg:
        eval_data["baseline_positives"].append(new_rev)
    else:
        eval_data["baseline_negatives"].append(new_rev)

    # performance interaction classification
    perf_inters: 'tp.Optional[tp.Iterable[PerfInteraction]]' = None
    if report:
        perf_inters = report.performance_interactions

    if perf_inters:
        eval_data["rq1_predicted_positives"].append(new_rev)
    else:
        eval_data["rq1_predicted_negatives"].append(new_rev)

    # RQ2
    if perf_inters:
        relevant_features: tp.Set[str] = set()

        for inter in perf_inters:
            relevant_features.update(inter.involved_features)

        relevant_configs = get_relevant_configs(
            project_name, configs, relevant_features
        )

        is_reg2 = get_num_regressions(
            performance_data, old_rev, new_rev, relevant_configs, threshold,
            sigma, min_diff, ignore_old_zero
        ) > 0

        if is_reg2:
            eval_data["rq2_predicted_positives"].append(new_rev)
        else:
            eval_data["rq2_predicted_negatives"].append(new_rev)


def calculate_case_study_data(
    project_name: str, performance_data: pd.DataFrame,
    revision_pairs: tp.Iterable[tp.Tuple[Revision,
                                         Revision]], configs: ConfigurationMap,
    perf_inter_reports: tp.Dict[Revision, PerformanceInteractionReport],
    threshold: float, sigma: float, min_diff: float, ignore_old_zero: bool
) -> pd.DataFrame:
    eval_data: EvalData = tp.cast(EvalData, defaultdict(list))

    for old_rev, new_rev in revision_pairs:
        if (
            old_rev not in performance_data.columns or
            new_rev not in performance_data.columns
        ):
            continue

        report = perf_inter_reports.get(new_rev, None)
        calculate_eval_data(
            project_name, performance_data, old_rev, new_rev, configs, report,
            threshold, sigma, min_diff, ignore_old_zero, eval_data
        )

    confusion_matrix = ConfusionMatrix(
        eval_data["baseline_positives"],
        eval_data["baseline_negatives"],
        eval_data["rq1_predicted_positives"],
        eval_data["rq1_predicted_negatives"],
    )

    rq2_confusion_matrix = ConfusionMatrix(
        list(
            set(eval_data["baseline_positives"]
               ).intersection(set(eval_data["rq1_predicted_positives"]))
        ),
        list(
            set(eval_data["baseline_negatives"]
               ).intersection(set(eval_data["rq1_predicted_positives"]))
        ),
        eval_data["rq2_predicted_positives"],
        eval_data["rq2_predicted_negatives"],
    )
    assert rq2_confusion_matrix.FP == 0, f"{project_name}: encountered FP in RQ2. This should not be possible!"

    cs_data: tp.Dict[tp.Any, tp.Any] = {
        ("Project", ""): [project_name],
        # RQ1
        ("RQ1", "Scenarios"): [confusion_matrix.P + confusion_matrix.N],
        ("RQ1", "P"): [confusion_matrix.P],
        ("RQ1", "PP"): [confusion_matrix.PP],
        ("RQ1", "TP"): [confusion_matrix.TP],
        ("RQ1", "Precision"): [confusion_matrix.precision()],
        ("RQ1", "Recall"): [confusion_matrix.recall()],
        # RQ2
        ("RQ2", "Scenarios"): [rq2_confusion_matrix.P + rq2_confusion_matrix.N],
        ("RQ2", "P"): [rq2_confusion_matrix.P],
        ("RQ2", "PP"): [rq2_confusion_matrix.PP],
        ("RQ2", "Recall"): [rq2_confusion_matrix.recall()]
    }

    cs_df = pd.DataFrame.from_dict(cs_data)
    cs_df.set_index("Project", inplace=True)
    return cs_df


class SavingsData(tp.TypedDict):
    project_name: str
    revision: Revision
    regression: bool
    predicted_regression: bool
    detected_regression: bool
    configs: int
    relevant_configs: int
    regressing_configs: int
    regressing_relevant_configs: int
    features: int
    relevant_features: int
    total_time: float
    relevant_time: float


def calculate_saved_costs(
    project_name: str, old_rev: Revision, new_rev: Revision,
    configs: ConfigurationMap, perf_inter_report: PerformanceInteractionReport,
    performance_data: pd.DataFrame, threshold: float, sigma: float,
    min_diff: float, ignore_old_zero: bool
) -> SavingsData:
    # RQ3
    features: tp.Set[str] = set(f.name for f in CONFIG_DATA[project_name])
    relevant_features: tp.Set[str] = set()
    predicted_regression = False

    for inter in perf_inter_report.performance_interactions:
        predicted_regression = True
        relevant_features.update(
            f for f in inter.involved_features if f in features
        )

    relevant_configs = get_relevant_configs(
        project_name, configs, relevant_features
    )

    regressing_configs = get_regressing_configs(
        performance_data, old_rev, new_rev, configs, threshold, sigma, min_diff,
        ignore_old_zero
    )

    num_configs = len(configs.ids())
    num_relevant_configs = len(relevant_configs.ids())
    num_regressing_configs = len(regressing_configs.ids())
    num_regressing_relevant_configs = len(
        set(relevant_configs.ids()).intersection(regressing_configs.ids())
    )

    t_baseline = 0.0
    t_rq3 = 0.0

    for config_id, config in configs.id_config_tuples():
        new_vals = get_performance_data(performance_data, new_rev, config_id)
        t_baseline += float(np.average(new_vals))

    for config_id in relevant_configs.ids():
        new_vals = get_performance_data(performance_data, new_rev, config_id)
        t_rq3 += float(np.average(new_vals))

    return {
        "project_name": project_name,
        "revision": new_rev,
        "regression": num_regressing_configs > 0,
        "predicted_regression": predicted_regression,
        "detected_regression": num_regressing_relevant_configs > 0,
        "configs": num_configs,
        "relevant_configs": num_relevant_configs,
        "regressing_configs": num_regressing_configs,
        "regressing_relevant_configs": num_regressing_relevant_configs,
        "features": len(features),
        "relevant_features": len(relevant_features),
        "total_time": t_baseline,
        "relevant_time": t_rq3
    }


class PerformanceRegressionClassificationTable(Table, table_name="perf_reg"):
    """Table for performance regression classification analysis."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        threshold = self.table_kwargs["threshold"]  # % diff
        sigma = self.table_kwargs["sigma"]  # times std
        min_diff = self.table_kwargs["min_diff"]

        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            commit_map = get_commit_map(project_name)
            revisions = sorted(case_study.revisions, key=commit_map.time_id)

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )

            performance_data = \
                PerformanceEvolutionDatabase.get_data_for_project(
                    project_name, ["revision", "config_id", "wall_clock_time"],
                    commit_map,
                    case_study,
                    cached_only=False
                ).pivot(
                    index="config_id", columns="revision",
                    values="wall_clock_time"
                )[[revision.to_short_commit_hash() for revision in revisions]]

            perf_inter_report_files = get_processed_revisions_files(
                project_name,
                PerformanceInteractionExperiment,
                file_name_filter=get_case_study_file_name_filter(case_study)
            )
            perf_inter_reports: tp.Dict[
                Revision, PerformanceInteractionReport] = {
                    report_file.report_filename.commit_hash:
                        load_performance_interaction_report(report_file)
                    for report_file in perf_inter_report_files
                }

            revision_pairs = pairwise([
                rev.to_short_commit_hash() for rev in revisions
            ])

            data.append(
                calculate_case_study_data(
                    project_name,
                    performance_data,
                    revision_pairs,
                    configs,
                    perf_inter_reports,
                    threshold,
                    sigma,
                    min_diff,
                    ignore_old_zero=True
                )
            )

        df = pd.concat(data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "l|rrrrrr|rrrr"
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


OPTIONAL_THRESHOLD: CLIOptionTy = make_cli_option(
    "--threshold",
    type=float,
    default=0.1,
    required=False,
    metavar="THRESHOLD",
    help="Only consider regressions where the performance difference is greater"
    "than the given threshold."
)

OPTIONAL_SIGMA: CLIOptionTy = make_cli_option(
    "--sigma",
    type=float,
    default=3,
    required=False,
    metavar="SIGMA",
    help="Only consider regressions that are at least SIGMA times greater than "
    "the standard deviation of the measurements."
)

OPTIONAL_MIN_DIFF: CLIOptionTy = make_cli_option(
    "--min-diff",
    type=float,
    default=0,
    required=False,
    metavar="MIN_DIFF",
    help="Only consider regressions that are at least MIN_DIFF large."
)


class PerformanceRegressionClassification(
    TableGenerator,
    generator_name="perf-reg",
    options=[OPTIONAL_THRESHOLD, OPTIONAL_SIGMA, OPTIONAL_MIN_DIFF],
):
    """Generates a table that does a precision/recall analysis for performance
    regression detection for multiple thresholds."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceRegressionClassificationTable(
                self.table_config, **self.table_kwargs
            )
        ]


class PerformanceInteractionSavingsTable(Table, table_name="perf_inter_cost"):
    """Table showing potential cost savings from performance interaction
    analysis."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[tp.Dict[str, tp.Any]] = []

        for case_study in case_studies:
            project_name = case_study.project_name
            commit_map = get_commit_map(project_name)
            revisions = sorted(case_study.revisions, key=commit_map.time_id)

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )
            features = {
                option.name
                for config in configs.configurations()
                for option in config.options()
            }

            performance_data = \
                PerformanceEvolutionDatabase.get_data_for_project(
                    project_name, ["revision", "config_id", "wall_clock_time"],
                    commit_map,
                    case_study,
                    cached_only=False
                ).pivot(
                    index="config_id", columns="revision",
                    values="wall_clock_time"
                )[[revision.to_short_commit_hash() for revision in revisions]]

            perf_inter_report_files = get_processed_revisions_files(
                project_name,
                PerformanceInteractionExperiment,
                file_name_filter=get_case_study_file_name_filter(case_study)
            )
            perf_inter_reports: tp.Dict[
                Revision, PerformanceInteractionReport] = {
                    report_file.report_filename.commit_hash:
                        load_performance_interaction_report(report_file)
                    for report_file in perf_inter_report_files
                }

            revision_pairs = pairwise([
                rev.to_short_commit_hash() for rev in revisions
            ])

            cs_data = []

            for old_rev, new_rev in revision_pairs:
                perf_inter_report = perf_inter_reports.get(new_rev, None)

                if perf_inter_report:
                    savings = calculate_saved_costs(
                        project_name,
                        old_rev,
                        new_rev,
                        configs,
                        perf_inter_report,
                        performance_data,
                        threshold=0.1,
                        sigma=3,
                        min_diff=0,
                        ignore_old_zero=True
                    )
                else:
                    savings = {
                        "project_name": project_name,
                        "revision": new_rev,
                        "regression": False,
                        "predicted_regression": False,
                        "detected_regression": False,
                        "configs": len(configs.ids()),
                        "relevant_configs": len(configs.ids()),
                        "regressing_configs": 0,
                        "regressing_relevant_configs": 0,
                        "features": len(features),
                        "relevant_features": len(features),
                        "total_time": np.nan,
                        "relevant_time": np.nan
                    }

                cs_data.append(savings)

            project_df = pd.DataFrame.from_records(cs_data)
            # write data as csv
            project_df.to_csv(f"tables/{project_name}_cost.txt", sep=" ")
            # table contains per-project summary
            predicted_df = project_df[project_df["predicted_regression"]]
            data.append({
                "Project": f"{project_name}",
                "$|F|$":
                    predicted_df["features"].median(),  # should be constant
                "$|\hat{F}|$": predicted_df["relevant_features"].mean(),
                "$|C|$": predicted_df["configs"].median(),  # should be constant
                "$|\hat{C}|$": predicted_df["relevant_configs"].mean(),
                "$T_{C} ($s$)$": predicted_df["total_time"].mean(),
                "$T_{\hat{C}} ($s$)$": predicted_df["relevant_time"].mean(),
            })

        df = pd.DataFrame.from_records(data)
        df.set_index("Project", inplace=True)

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "lrrrrrr"
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


class PerformanceInteractionSavings(
    TableGenerator, generator_name="perf-inter-cost", options=[]
):
    """Generates a table showing potential cost savings from performance
    interaction analysis."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceInteractionSavingsTable(
                self.table_config, **self.table_kwargs
            )
        ]


def load_synth_baseline_data(
    case_study: CaseStudy, config_ids: tp.List[int]
) -> pd.DataFrame:
    project_name = case_study.project_name

    data: tp.List[tp.Dict[str, tp.Any]] = []
    time_report_dict = get_files_with_status_by_config(
        project_name, [FileStatusExtension.SUCCESS],
        PerfSamplingSynth,
        MPRWLTimeReportAggregate,
        file_name_filter=get_case_study_file_name_filter(case_study),
        only_newest=True,
        config_ids=config_ids
    )

    for config_id in config_ids:
        time_report_files = time_report_dict.get(config_id, [])

        if not time_report_files:
            LOG.warning(
                f"No baseline report found for {project_name}:{config_id}, skipping."
            )
            continue

        assert len(time_report_files) == 1
        time_report = load_mpr_wl_time_report_aggregate(time_report_files[0])

        baseline_report = time_report.get_baseline_report()
        assert baseline_report is not None
        assert len(baseline_report.workload_names()) == 1
        workload = next(iter(baseline_report.workload_names()))
        data.append({
            "revision":
                "base",
            "config_id":
                config_id,
            "wall_clock_time":
                baseline_report.measurements_wall_clock_time(workload)
        })

        for patch_name in time_report.get_patch_names():
            patched_report = time_report.get_report_for_patch(patch_name)
            assert patched_report is not None
            assert len(patched_report.workload_names()) == 1
            workload = next(iter(patched_report.workload_names()))
            data.append({
                "revision":
                    patch_name,
                "config_id":
                    config_id,
                "wall_clock_time":
                    patched_report.measurements_wall_clock_time(workload)
            })

    return pd.DataFrame.from_records(data)


def load_synth_perf_inter_reports(
    case_study: CaseStudy
) -> tp.Dict[Revision, PerformanceInteractionReport]:
    project_name = case_study.project_name

    report_files = get_processed_revisions_files(
        project_name,
        PerformanceInteractionExperimentSynthetic,
        file_name_filter=get_case_study_file_name_filter(case_study),
        only_newest=True
    )

    if not report_files:
        LOG.warning(
            f"No performance interaction report found for {project_name}, skipping."
        )
        return {}

    assert len(report_files) == 1
    report = load_mpr_performance_interaction_report(report_files[0])
    report_dict: tp.Dict[Revision, PerformanceInteractionReport] = {}

    for patch_name in report.get_patch_names():
        patch_report = report.get_report_for_patch(patch_name)
        assert patch_report is not None
        report_dict[patch_name] = patch_report

    return report_dict


class PerformanceRegressionClassificationTableSynth(
    Table, table_name="perf_reg_synth"
):
    """Table for performance regression classification analysis for synthetic
    case studies."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        threshold = self.table_kwargs["threshold"]  # % diff
        sigma = self.table_kwargs["sigma"]  # times std
        min_diff = self.table_kwargs["min_diff"]

        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )

            performance_data = load_synth_baseline_data(
                case_study, configs.ids()
            )

            if performance_data.empty:
                continue

            revisions = performance_data["revision"].unique().tolist()
            revisions.remove("base")
            performance_data = performance_data.pivot(
                index="config_id", columns="revision", values="wall_clock_time"
            )
            perf_inter_reports = load_synth_perf_inter_reports(case_study)
            revision_pairs = [("base", patch_name) for patch_name in revisions]

            data.append(
                calculate_case_study_data(
                    project_name,
                    performance_data,
                    revision_pairs,
                    configs,
                    perf_inter_reports,
                    threshold,
                    sigma,
                    min_diff,
                    ignore_old_zero=False
                )
            )

        df = pd.concat(data).sort_index()

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "l|rrrrrr|rrrr"
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


class PerformanceRegressionClassificationSynth(
    TableGenerator,
    generator_name="perf-reg-synth",
    options=[OPTIONAL_THRESHOLD, OPTIONAL_SIGMA, OPTIONAL_MIN_DIFF]
):
    """Generates a table that does a precision/recall analysis for performance
    regression detection for multiple thresholds."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceRegressionClassificationTableSynth(
                self.table_config, **self.table_kwargs
            )
        ]


class PerformanceInteractionSavingsTableSynth(
    Table, table_name="perf_inter_cost_synth"
):
    """Table showing potential cost savings from performance interaction
    analysis."""

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        data: tp.List[tp.Dict[str, tp.Any]] = []

        for case_study in case_studies:
            project_name = case_study.project_name

            configs = load_configuration_map_for_case_study(
                get_paper_config(), case_study, PlainCommandlineConfiguration
            )
            features = {
                option.name
                for config in configs.configurations()
                for option in config.options()
            }

            performance_data = load_synth_baseline_data(
                case_study, configs.ids()
            )

            if performance_data.empty:
                continue

            revisions = performance_data["revision"].unique().tolist()
            revision_pairs = [("base", patch_name)
                              for patch_name in sorted(revisions)
                              if patch_name != "base"]
            performance_data = performance_data.pivot(
                index="config_id", columns="revision", values="wall_clock_time"
            )
            perf_inter_reports = load_synth_perf_inter_reports(case_study)

            cs_data = []

            for old_rev, new_rev in revision_pairs:
                perf_inter_report = perf_inter_reports.get(new_rev, None)

                if perf_inter_report:
                    savings = calculate_saved_costs(
                        project_name,
                        old_rev,
                        new_rev,
                        configs,
                        perf_inter_report,
                        performance_data,
                        threshold=0.1,
                        sigma=3,
                        min_diff=0,
                        ignore_old_zero=False
                    )
                else:
                    savings = {
                        "project_name": project_name,
                        "revision": new_rev,
                        "regression": False,
                        "predicted_regression": False,
                        "detected_regression": False,
                        "configs": len(configs.ids()),
                        "relevant_configs": len(configs.ids()),
                        "regressing_configs": 0,
                        "regressing_relevant_configs": 0,
                        "features": len(features),
                        "relevant_features": len(features),
                        "total_time": np.nan,
                        "relevant_time": np.nan
                    }

                cs_data.append(savings)

            project_df = pd.DataFrame.from_records(cs_data)
            # write data as csv
            project_df.to_csv(f"tables/{project_name}_cost.txt", sep=" ")
            # table contains per-project summary
            predicted_df = project_df[project_df["predicted_regression"]]
            data.append({
                "Project": f"{project_name}",
                "$|F|$":
                    predicted_df["features"].median(),  # should be constant
                "$|\hat{F}|$": predicted_df["relevant_features"].mean(),
                "$|C|$": predicted_df["configs"].median(),  # should be constant
                "$|\hat{C}|$": predicted_df["relevant_configs"].mean(),
                "$T_{C} ($s$)$": predicted_df["total_time"].mean(),
                "$T_{\hat{C}} ($s$)$": predicted_df["relevant_time"].mean(),
            })

        df = pd.DataFrame.from_records(data)
        df.set_index("Project", inplace=True)

        style = df.style
        kwargs: tp.Dict[str, tp.Any] = {}
        if table_format.is_latex():
            kwargs["hrules"] = True
            kwargs["column_format"] = "lrrrrrr"
            kwargs["multicol_align"] = "c"
            style.format(precision=2, thousands=r"\,")

        return dataframe_to_table(
            df, table_format, style, wrap_table, wrap_landscape=True, **kwargs
        )


class PerformanceInteractionSavingsSynth(
    TableGenerator, generator_name="perf-inter-cost-synth", options=[]
):
    """Generates a table showing potential cost savings from performance
    interaction analysis."""

    def generate(self) -> tp.List[Table]:
        return [
            PerformanceInteractionSavingsTableSynth(
                self.table_config, **self.table_kwargs
            )
        ]
