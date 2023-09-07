import textwrap
from pathlib import Path

from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult
from plumbum import ProcessExecutionError

from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import Patch
from varats.utils.git_commands import apply_patch, revert_patch


class ApplyPatch(actions.ProjectStep):
    """Apply a patch to a project."""

    NAME = "APPLY_PATCH"
    DESCRIPTION = "Apply a Git patch to a project."

    def __init__(self, project: VProject, patch: Patch) -> None:
        super().__init__(project)
        self.__patch = patch

    def __call__(self) -> StepResult:
        try:
            print(
                f"Applying {self.__patch.shortname} to "
                f"{self.project.source_of_primary}"
            )
            apply_patch(Path(self.project.source_of_primary), self.__patch.path)

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        self.status = StepResult.OK

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Apply patch "
            f"{self.__patch.shortname}", " " * indent
        )


class RevertPatch(actions.ProjectStep):
    """Revert a patch from a project."""

    NAME = "REVERT_PATCH"
    DESCRIPTION = "Revert a Git patch from a project."

    def __init__(self, project, patch):
        super().__init__(project)
        self.__patch = patch

    def __call__(self) -> StepResult:
        try:
            print(
                f"Reverting {self.__patch.shortname} on "
                f"{self.project.source_of_primary}"
            )
            revert_patch(
                Path(self.project.source_of_primary), self.__patch.path
            )

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        self.status = StepResult.OK

        return StepResult.OK

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: Revert patch "
            f"{self.__patch.shortname}", " " * indent
        )
