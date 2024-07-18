import typing as tp

from benchbuild.extensions import run, compiler
from benchbuild.utils import actions

from varats.experiment.experiment_util import (
    VersionExperiment,
    get_default_compile_error_wrapped,
)
from varats.project.varats_project import VProject


class FindHiddenConfigurationPoints(VersionExperiment, shorthand="HCP"):
    """Detects hidden configurability points in the project."""

    NAME = "FindHiddenConfigurationPoints"

    def actions_for_project(self, project: VProject) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        # Add the required runtime extensions to the project(s).
        project.runtime_extension = run.RuntimeExtension(project, self)

        # Add the required compiler extensions to the project(s).
        project.compiler_extension = compiler.RunCompiler(project, self) \
                                     << run.WithTimeout()

        project.compile = get_default_compile_error_wrapped(
            self.get_handle(), project, self.REPORT_SPEC.main_report
        )
