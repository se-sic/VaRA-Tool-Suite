"""Module for feature performance experiments that instrument and measure the
execution performance of each binary that is produced by a project."""
import typing as tp

from benchbuild.extensions import compiler, run, time
from benchbuild.utils import actions
from benchbuild.environments.domain.declarative import ContainerImage

from varats.experiment.experiment_util import (
    get_default_compile_error_wrapped,
    WithUnlimitedStackSize,
)
from varats.experiments.vara.feature_experiment import (
    FeatureExperiment,
    RunVaRATracedWorkloads,
    RunVaRATracedXRayWorkloads,
    FeatureInstrType,
)
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification
from varats.report.tef_report import TEFReport


class FeaturePerfRunner(FeatureExperiment, shorthand="FPR"):
    """Test runner for feature performance."""

    NAME = "RunFeaturePerf"

    REPORT_SPEC = ReportSpecification(TEFReport)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        instr_type = FeatureInstrType.TEF

        project.cflags += self.get_vara_feature_cflags(project)

        project.cflags += self.get_vara_tracing_cflags(
            instr_type, project=project
        )

        project.ldflags += self.get_vara_tracing_ldflags()

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << WithUnlimitedStackSize()

        # Add own error handler to compile step.
        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TEFReport
        )

        analysis_actions = []

        analysis_actions.append(actions.Compile(project))
        analysis_actions.append(
            RunVaRATracedWorkloads(project, self.get_handle())
        )
        analysis_actions.append(actions.Clean(project))

        return analysis_actions


class FeaturePerfVaRAXRayRunner(FeatureExperiment, shorthand="FPVXR"):
    """Test runner for feature performance with XRay."""

    NAME = "RunFeatureVaRAXRayPerf"

    REPORT_SPEC = ReportSpecification(TEFReport)

    CONTAINER = ContainerImage().run("apt", "install", "-y", "time")

    def actions_for_project(
        self,
        project: VProject,
        enable_vara: bool = True,
        enable_xray: bool = True
    ) -> tp.MutableSequence[actions.Step]:
        if enable_vara:
            print("VaRA enabled")
            project.cflags += self.get_vara_feature_cflags(project)

            project.cflags += self.get_vara_tracing_cflags(
                FeatureInstrType.TEF, project=project, instruction_threshold=0
            )

            project.ldflags += self.get_vara_tracing_ldflags()

        if enable_xray:
            print("XRay enabled")
            project.cflags += [
                "-fxray-instrument",
                "-fxray-instruction-threshold=200",
            ]

        print(project.cflags)

        project.cflags += [
            "-flto",
            "-fuse-ld=lld",
        ]

        project.ldflags += [
            "-flto",
        ]

        project.runtime_extension = run.RuntimeExtension(project, self) \
            << time.RunWithTime()

        project.compiler_extension = compiler.RunCompiler(project, self) \
            << WithUnlimitedStackSize()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, TEFReport
        )

        return [
            actions.Compile(project),
            RunVaRATracedXRayWorkloads(
                project,
                self.get_handle(),
                enable_vara,
                enable_xray,
                num_iterations=10
            ),
            actions.Clean(project),
        ]


class FeaturePerfXRayRunner(FeaturePerfVaRAXRayRunner, shorthand="FRXR"):

    NAME = "RunFeatureXRayPerf"

    def actions_for_project(self, project: VProject,
                            **kwargs) -> tp.MutableSequence[actions.Step]:
        return super().actions_for_project(
            project, enable_vara=False, enable_xray=True
        )


class FeaturePerfVaRARunner(FeaturePerfVaRAXRayRunner, shorthand="FPVR"):

    NAME = "RunFeatureVaRAPerf"

    def actions_for_project(self, project: VProject,
                            **kwargs) -> tp.MutableSequence[actions.Step]:
        return super().actions_for_project(
            project, enable_vara=True, enable_xray=False
        )


class FeaturePerfBaseRunner(FeaturePerfVaRAXRayRunner, shorthand="FPBR"):

    NAME = "RunFeatureBasePerf"

    def actions_for_project(self, project: VProject,
                            **kwargs) -> tp.MutableSequence[actions.Step]:
        return super().actions_for_project(
            project, enable_vara=False, enable_xray=False
        )
