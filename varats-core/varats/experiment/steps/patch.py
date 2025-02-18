import textwrap
from pathlib import Path

from benchbuild.utils import actions
from benchbuild.utils.actions import StepResult
from plumbum import ProcessExecutionError

from varats.project.varats_project import VProject
from varats.provider.patch.patch_provider import Patch
from varats.utils.git_commands import apply_patch, revert_patch
from varats.utils.git_util import RepositoryHandle

def _build_args_string(args: dict) -> str:
    return ", ".join([f"{k}={v}" for k, v in args.items()])

class ApplyPatch(actions.ProjectStep):
    """Apply a patch to a project."""

    NAME = "APPLY_PATCH"
    DESCRIPTION = "Apply a Git patch to a project."

    def __init__(self, project: VProject, patch: Patch, **kwargs) -> None:
        super().__init__(project)
        self.__patch = patch
        self.__arguments = kwargs

    def __call__(self) -> StepResult:
        self.status = StepResult.OK
        print(
            f"Applying {self.__patch.shortname} to "
            f"{self.project.source_of_primary}"
        )

        patch_path = self.__patch.render(**self.__arguments)

        try:
            apply_patch(RepositoryHandle(Path(self.project.source_of_primary))
                        , patch_path)

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        out = f"* {self.project.name}: Apply patch {self.__patch.shortname}"
        if self.__arguments:
            out += f" (Arguments: {_build_args_string(self.__arguments)})"

        return textwrap.indent(
            out, " " * indent
        )


class RevertPatch(actions.ProjectStep):
    """Revert a patch from a project."""

    NAME = "REVERT_PATCH"
    DESCRIPTION = "Revert a Git patch from a project."

    def __init__(self, project: VProject, patch: Patch, **kwargs) -> None:
        super().__init__(project)
        self.__patch = patch
        self.__arguments = kwargs

    def __call__(self) -> StepResult:
        self.status = StepResult.OK
        print(
            f"Reverting {self.__patch.shortname} on "
            f"{self.project.source_of_primary}"
        )

        patch_path = self.__patch.render(**self.__arguments)

        try:
            revert_patch(
                RepositoryHandle(Path(self.project.source_of_primary)),
                patch_path
            )

        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        out = f"* {self.project.name}: Revert patch {self.__patch.shortname}"
        if self.__arguments:
            out += f" (Arguments: {_build_args_string(self.__arguments)})"

        return textwrap.indent(
            out, " " * indent
        )
