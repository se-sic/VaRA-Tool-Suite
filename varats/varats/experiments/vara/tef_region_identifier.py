import json
from pathlib import Path

from benchbuild.utils import actions
from benchbuild.utils.actions import Step, StepResult, ProjectStep
import benchbuild.extensions as bb_ext

from varats.data.databases.feature_perf_precision_database import get_feature_regions_from_tef_report
from varats.data.reports.tef_feature_identifier_report import TEFFeatureIdentifierReport
from varats.experiment.experiment_util import WithUnlimitedStackSize, get_default_compile_error_wrapped, \
    create_new_success_result_filepath, get_config_patch_steps, ZippedExperimentSteps
from varats.experiment.steps.patch import ApplyPatch, RevertPatch
from varats.experiment.steps.recompile import ReCompile
from varats.experiments.vara.feature_experiment import FeatureExperiment, FeatureInstrType
from varats.experiments.vara.feature_perf_precision import get_extra_cflags, MPRTEFAggregate, select_project_binaries, \
    RunGenTracedWorkloads
from varats.project.project_util import BinaryType
from varats.project.varats_project import VProject

import typing as tp

from varats.provider.patch.patch_provider import PatchProvider
from varats.report.multi_patch_report import MultiPatchReport
from varats.report.report import ReportSpecification
from varats.utils.config import get_current_config_id
from varats.utils.git_util import ShortCommitHash


class TEFFeatureIdentifier(FeatureExperiment, shorthand="TEFid"):
    NAME = "RunTEFIdentifier"

    REPORT_SPEC = TEFFeatureIdentifierReport

    def actions_for_project(self,
                            project: VProject) -> tp.MutableSequence[Step]:
        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(
            FeatureInstrType.TEF,
            project=project,
            save_temps=True,
            instruction_threshold=0
        )

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
            self.get_handle(), project, ReportSpecification(MPRTEFAggregate).main_report
        )

        # TODO: change to multiple binaries
        binary = select_project_binaries(project)[0]
        if binary.type != BinaryType.EXECUTABLE:
            raise AssertionError("Experiment only works with executables.")

        tmp_tef_result = create_new_success_result_filepath(
            self.get_handle(),
            MPRTEFAggregate, project, binary,
            get_current_config_id(project)
        )

        patch_provider = PatchProvider.get_provider_for_project(project)

        patches = patch_provider.get_patches_for_revision(
            ShortCommitHash(project.version_of_primary)
        )["region_identifier"]

        patch_steps = []
        for patch in patches:
            print(f"Got patch with path: {patch.path}")
            patch_steps.append(ApplyPatch(project, patch))
            patch_steps.append(ReCompile(project))
            patch_steps.append(
                RunGenTracedWorkloads(
                    project,
                    binary,
                    file_name=MultiPatchReport.create_patched_report_name(
                        patch, "feature_id"
                    ),
                    reps=1
                )
            )
            patch_steps.append(RevertPatch(project, patch))

        analysis_actions = get_config_patch_steps(project)

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            ZippedExperimentSteps(
                tmp_tef_result, [
                                    RunGenTracedWorkloads(
                                        project,
                                        binary,
                                        file_name=MultiPatchReport.
                                        create_baseline_report_name("feature_id"),
                                        reps=1
                                    )
                                ] + patch_steps
            )
        )
        analysis_actions.append(actions.Clean(project))

        mpr_tef_report = MPRTEFAggregate(tmp_tef_result.full_path())
        analysis_actions.append(AnalyzeMPRTEFTrace(mpr_tef_report))

        return analysis_actions


class AnalyzeMPRTEFTrace(ProjectStep):
    NAME = "VaRAAnalyzeMPRTEFTrace"
    DESCRIPTION = "Analyze a MPRTEFAggregateReport to identify all regions and interactions"

    project: VProject

    def __init__(self, file_name: Path, mpr_tef_report: MPRTEFAggregate):
        self.__report = mpr_tef_report
        self.__file_name = file_name
        pass

    def __call__(self):
        result_dict = {}

        base_report = self.__report.get_baseline_report()

        tef_report = base_report.reports()[0]

        result_dict["Baseline"] = get_feature_regions_from_tef_report(tef_report)

        for patch in self.__report.get_patch_names():
            tef_report = self.__report.get_report_for_patch(patch).reports()[0]

            result_dict[f"PATCHED_{patch}"] = get_feature_regions_from_tef_report(tef_report)

        with open(self.__file_name, "w ") as f:
            json.dump(result_dict, f)

        return StepResult.OK
