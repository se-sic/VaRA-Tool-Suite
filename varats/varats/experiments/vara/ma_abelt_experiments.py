"""Module for experiments run in the master thesis of Lukas Abelt."""
import json
import math
import typing as tp
from collections import defaultdict
from itertools import chain, combinations

import benchbuild.extensions as bb_ext
from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.utils import actions

from varats.data.reports.tef_feature_identifier_report import (
    TEFFeatureIdentifierReport,
)
from varats.experiment.experiment_util import (
    WithUnlimitedStackSize,
    create_new_success_result_filepath,
    get_default_compile_error_wrapped,
    ZippedExperimentSteps,
    get_config_patch_steps,
    get_varats_result_folder,
)
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    FeatureInstrType,
)
from varats.experiments.vara.feature_perf_precision import (
    RunBackBoxBaseline,
    AnalysisProjectStepBase,
    MPRTEFAggregate,
    MPRPIMAggregate,
    MPRTimeReportAggregate,
    RunGenTracedWorkloads,
    RunBPFTracedWorkloads,
    get_extra_cflags,
    get_threshold,
)
from varats.experiments.vara.ma_abelt_utils import (
    get_tags_RQ1,
    select_project_binaries,
)
from varats.experiments.vara.tef_region_identifier import TEFFeatureIdentifier
from varats.paper.paper_config import get_paper_config
from varats.paper_mgmt.case_study import get_case_study_file_name_filter
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import PatchProvider, PatchSet
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash

REPS = 30

IDENTIFIER_PATCH_TAG = 'perf_prec'


def default_patch_selector(project):
    patch_provider = PatchProvider.get_provider_for_project(project)
    patches = patch_provider.get_patches_for_revision(
        ShortCommitHash(project.version_of_primary)
    )[IDENTIFIER_PATCH_TAG]

    return [(p.shortname, [p]) for p in patches]


def RQ1_patch_selector(project):
    rq1_tags = get_tags_RQ1(project)

    patch_provider = PatchProvider.get_provider_for_project(project)

    patches = PatchSet(set())

    for tag in rq1_tags:
        patches |= patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )[tag, "regression"]

    return [(p.shortname, [p]) for p in patches]


def RQ2_patch_selector(project: VProject):
    MAX_PATCHES = 5

    paper_config = get_paper_config()
    case_studies = paper_config.get_case_studies(cs_name=project.name)
    current_config = get_current_config_id(project)

    report_files = get_processed_revisions_files(
        project.name,
        TEFFeatureIdentifier,
        TEFFeatureIdentifierReport,
        get_case_study_file_name_filter(case_studies[0]),
        config_id=current_config
    )

    if len(report_files) != 1:
        print("Invalid number of reports from TEFIdentifier")
        return []

    report_file = TEFFeatureIdentifierReport(report_files[0].full_path())

    patch_names = select_non_interacting_patches(report_file)
    patch_names += select_interacting_patches(
        report_file, patch_names, MAX_PATCHES - len(patch_names)
    )
    patch_names += greedily_select_patches(
        report_file, patch_names, MAX_PATCHES - len(patch_names)
    )

    SEVERITY = "1000ms"

    patch_names = [p[:-len("detect")] + SEVERITY for p in patch_names]

    patch_tuples = chain.from_iterable(
        combinations(patch_names, r) for r in range(1,
                                                    len(patch_names) + 1)
    )

    patch_provider = PatchProvider.get_provider_for_project(project)

    result = [(
        f"patchlist-{i}",
        [patch_provider.get_by_shortname(p_name) for p_name in p_tuple]
    ) for i, p_tuple in enumerate(patch_tuples)]

    return result


def select_non_interacting_patches(
    report_file: TEFFeatureIdentifierReport, count: int = 3
):
    patch_candidates = {}
    region_candidates = defaultdict(lambda: math.inf)

    for region in report_file.affectable_regions:
        # We only consider regions that affect one other feature
        if len(region) != 2 or "__VARA__DETECT__" not in region:
            continue

        # Check all patches that affect exactly this region
        for patch in report_file.patches_for_regions(region):
            patch_name = patch[0]

            consider_patch = False
            num_affections = math.inf
            for patch_region in report_file.regions_for_patch(patch_name):
                # We do not care about unaffected regions
                if "__VARA__DETECT__" not in patch_region[0]:
                    continue

                # This is our region of interest
                if patch_region[0] == region:
                    consider_patch = True
                    num_affections = patch_region[1]
                    continue

                # At this point, we know that we don't want to consider the patch
                # It has the __VARA__DETECT__ interaction but is not our region of interest
                # That means that either also other regions are affected by this patch
                consider_patch = False
                break

            if consider_patch:
                if num_affections < region_candidates[region]:
                    patch_candidates[region] = (patch_name, num_affections)
                    region_candidates[region] = num_affections

    region_candidates = sorted(region_candidates.items(),
                               key=lambda kv: kv[1])[:count]
    patch_candidates = sorted(
        patch_candidates.items(), key=lambda kv: kv[1][1]
    )[:count]
    patch_names = [r[1][0] for r in patch_candidates]

    return patch_names


def select_interacting_patches(
    report_file: TEFFeatureIdentifierReport, selected_patches: tp.Iterable[str],
    count: int
):
    affected_regions = get_affected_regions(report_file, selected_patches)

    new_regions = defaultdict(set)

    for patch in report_file.patch_names:
        consider_patch = False
        new_patch_regions = set()
        if patch in selected_patches:
            continue
        for region in report_file.regions_for_patch(patch):
            # We want "interesting regions
            if "__VARA__DETECT__" not in region[0]:
                continue

            # We want to ensure that we have at least some interaction with the affected regions
            for affected_region in affected_regions:
                intersection = affected_region.intersection(region[0])
                if "__VARA__DETECT__" in intersection and len(intersection) > 1:
                    consider_patch = True
                    break

            # This region is already covered
            if region[0] in affected_regions:
                consider_patch = True
                continue

            new_patch_regions.add(region)

        if consider_patch:
            new_regions[patch] = new_patch_regions

    new_regions = sorted(
        new_regions.items(), key=lambda kv: len(kv[1]), reverse=True
    )

    return [r[0] for r in new_regions[:count]]


def greedily_select_patches(
    report_file: TEFFeatureIdentifierReport, selected_patches: tp.Iterable[str],
    count: int
):
    if count <= 0:
        return []
    result = []

    new_regions = defaultdict(set)
    for patch in report_file.patch_names:
        if patch in selected_patches:
            continue
        for region in report_file.regions_for_patch(patch):
            if "__VARA__DETECT__" not in region[0] or len(region[0]) < 2:
                continue

            new_regions[patch].add(region)

    new_regions = sorted(
        new_regions.items(), key=lambda kv: len(kv[1]), reverse=True
    )
    return [r[0] for r in new_regions[:count]]


def get_affected_regions(
    report_file: TEFFeatureIdentifierReport, patch_names: tp.Iterable[str]
):
    result = set()

    for patch in patch_names:
        for region in report_file.regions_for_patch(patch):
            if "__VARA__DETECT__" in region[0]:
                result.add(region[0])

    return result


def setup_actions_for_vara_experiment(
    experiment: FeatureExperiment,
    project: VProject,
    instr_type: FeatureInstrType,
    analysis_step: tp.Type[AnalysisProjectStepBase],
    patch_selector=RQ1_patch_selector,
    reps: int = REPS
) -> tp.MutableSequence[actions.Step]:
    project.cflags += experiment.get_vara_feature_cflags(project)

    threshold = get_threshold(project)
    project.cflags += experiment.get_vara_tracing_cflags(
        instr_type,
        project=project,
        save_temps=True,
        instruction_threshold=threshold
    )

    project.cflags += get_extra_cflags(project)

    project.ldflags += experiment.get_vara_tracing_ldflags()

    # Add the required runtime extensions to the project(s).
    project.runtime_extension = bb_ext.run.RuntimeExtension(
        project, experiment
    ) << bb_ext.time.RunWithTime()

    # Add the required compiler extensions to the project(s).
    project.compiler_extension = bb_ext.compiler.RunCompiler(
        project, experiment
    ) << WithUnlimitedStackSize()

    # Add own error handler to compile step.
    project.compile = get_default_compile_error_wrapped(
        experiment.get_handle(), project, experiment.REPORT_SPEC.main_report
    )

    # TODO: change to multiple binaries
    binary = select_project_binaries(project)[0]
    if binary.type != BinaryType.EXECUTABLE:
        raise AssertionError("Experiment only works with executables.")

    result_filepath = create_new_success_result_filepath(
        experiment.get_handle(),
        experiment.get_handle().report_spec().main_report, project, binary,
        get_current_config_id(project)
    )

    patchlists = patch_selector(project)

    # Save patch lists, so we can create a mapping from name <-> patches later if we need it
    save_path = get_varats_result_folder(
        project
    ) / f"{get_current_config_id(project)}-{experiment.shorthand()}.json"
    with open(save_path, "w") as f:
        patch_name_list = [(name, [patch.shortname
                                   for patch in p_list])
                           for name, p_list in patchlists]
        json.dump(patch_name_list, f)

    patch_steps = []
    for name, patches in patchlists:
        for patch in patches:
            patch_steps.append(ApplyPatch(project, patch))
        patch_steps.append(ReCompile(project))
        patch_steps.append(
            analysis_step(
                project,
                binary,
                file_name=MultiPatchReport.
                create_custom_named_patched_report_name(
                    name, "rep_measurements"
                ),
                reps=reps
            )
        )
        for patch in reversed(patches):
            patch_steps.append(RevertPatch(project, patch))

    analysis_actions = get_config_patch_steps(project)

    analysis_actions.append(actions.Compile(project))
    analysis_actions.append(
        ZippedExperimentSteps(
            result_filepath, [
                analysis_step(
                    project,
                    binary,
                    file_name=MultiPatchReport.
                    create_baseline_report_name("rep_measurements"),
                    reps=reps
                )
            ] + patch_steps
        )
    )
    analysis_actions.append(actions.Clean(project))

    return analysis_actions


########################################################################################################################
#
# Sensitivity Experiments
#
########################################################################################################################
class TEFProfileRunnerSeverity(FeatureExperiment, shorthand="TEFp-RQ1"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfilerSeverity"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self,
            project,
            FeatureInstrType.TEF,
            RunGenTracedWorkloads,
            RQ1_patch_selector,
            reps=REPS
        )


class PIMProfileRunnerSeverity(FeatureExperiment, shorthand="PIMp-RQ1"):
    """Runs the PIM profiler for the severity measurements."""

    NAME = "RunPIMProfilerSeverity"

    REPORT_SPEC = ReportSpecification(MPRPIMAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self,
            project,
            FeatureInstrType.PERF_INFLUENCE_TRACE,
            RunGenTracedWorkloads,
            RQ1_patch_selector,
            reps=REPS
        )


class EbpfTraceTEFProfileRunnerSeverity(
    FeatureExperiment, shorthand="ETEFp-RQ1"
):
    """Runs the EBPF trace profiler for the severity measurements."""

    NAME = "RunEBPFTraceTEFProfilerSeverity"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

    CONTAINER = ContainerImage().run('apt', 'install', '-y', 'bpftrace')

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self,
            project,
            FeatureInstrType.USDT_RAW,
            RunBPFTracedWorkloads,
            RQ1_patch_selector,
            reps=REPS
        )


class BlackBoxBaselineRunnerSeverity(FeatureExperiment, shorthand="BBBase-RQ1"):
    """Test runner for feature performance in RQ1."""

    NAME = "GenBBBaselineSeverity"

    REPORT_SPEC = ReportSpecification(MPRTimeReportAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-flto", "-fuse-ld=lld", "-fno-omit-frame-pointer"]

        project.cflags += get_extra_cflags(project)

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        # TODO: change to multiple binaries
        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        patchlists = RQ1_patch_selector(project)

        patch_steps = []
        for name, patches in patchlists:
            for patch in patches:
                # print(f"Got patch with path: {patch.path}")
                patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.append(
                RunBackBoxBaseline(
                    project,
                    binary,
                    file_name=MPRTimeReportAggregate.
                    create_custom_named_patched_report_name(
                        name, "rep_measurements"
                    ),
                    reps=REPS
                )
            )
            for patch in reversed(patches):
                patch_steps.append(RevertPatch(project, patch))

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    RunBackBoxBaseline(
                        project,
                        binary,
                        file_name=MPRTimeReportAggregate.
                        create_baseline_report_name("rep_measurements"),
                        reps=REPS
                    )
                ] + patch_steps
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


########################################################################################################################
#
# Precision, Recall & Accuracy
#
########################################################################################################################


class TEFProfileRunnerPrecision(FeatureExperiment, shorthand="TEFp-RQ2"):
    """Test runner for feature performance."""

    NAME = "RunTEFProfilerPrecision"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self,
            project,
            FeatureInstrType.TEF,
            RunGenTracedWorkloads,
            RQ2_patch_selector,
            reps=3
        )


class PIMProfileRunnerPrecision(FeatureExperiment, shorthand="PIMp-RQ2"):
    """Runs the PIM profiler for the severity measurements."""

    NAME = "RunPIMProfilerPrecision"

    REPORT_SPEC = ReportSpecification(MPRPIMAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self,
            project,
            FeatureInstrType.PERF_INFLUENCE_TRACE,
            RunGenTracedWorkloads,
            RQ2_patch_selector,
            reps=3
        )


class EbpfTraceTEFProfileRunnerPrecision(
    FeatureExperiment, shorthand="ETEFp-RQ2"
):
    """Runs the EBPF trace profiler for the severity measurements."""

    NAME = "RunEBPFTraceTEFProfilerPrecision"

    REPORT_SPEC = ReportSpecification(MPRTEFAggregate)

    CONTAINER = ContainerImage().run('apt', 'install', '-y', 'bpftrace')

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        return setup_actions_for_vara_experiment(
            self,
            project,
            FeatureInstrType.USDT_RAW,
            RunBPFTracedWorkloads,
            RQ2_patch_selector,
            reps=3
        )


class BlackBoxBaselineRunnerAccuracy(FeatureExperiment, shorthand="BBBase-RQ3"):
    """Test runner for feature performance in RQ3."""

    NAME = "GenBBBaselineAccuracy"

    REPORT_SPEC = ReportSpecification(MPRTimeReportAggregate)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        project.cflags += ["-flto", "-fuse-ld=lld", "-fno-omit-frame-pointer"]

        project.cflags += get_extra_cflags(project)

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = bb_ext.run.RuntimeExtension(
            project, self
        ) << bb_ext.time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = bb_ext.compiler.RunCompiler(
            project, self
        ) << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )

        # TODO: change to multiple binaries
        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        result_filepath = create_new_success_result_filepath(
            self.get_handle(),
            self.get_handle().report_spec().main_report, project, binary,
            get_current_config_id(project)
        )

        patchlists = RQ2_patch_selector(project)

        patch_steps = []
        for name, patches in patchlists:
            for patch in patches:
                patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.append(
                RunBackBoxBaseline(
                    project,
                    binary,
                    file_name=MPRTimeReportAggregate.
                    create_custom_named_patched_report_name(
                        name, "rep_measurements"
                    ),
                    reps=30
                )
            )
            for patch in reversed(patches):
                patch_steps.append(RevertPatch(project, patch))

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                result_filepath, [
                    RunBackBoxBaseline(
                        project,
                        binary,
                        file_name=MPRTimeReportAggregate.
                        create_baseline_report_name("rep_measurements"),
                        reps=REPS
                    )
                ] + patch_steps
            )
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions
