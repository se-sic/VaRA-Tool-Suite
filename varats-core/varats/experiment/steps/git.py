"""Git related project steps."""

import textwrap
import typing as tp
from pathlib import Path

from benchbuild.utils.actions import StepResult, ProjectStep
from plumbum import ProcessExecutionError

import varats.utils.git_commands as git
from varats.project.varats_project import VProject
from varats.utils.git_util import CommitHash


class GitAdd(ProjectStep):
    """Runs `git add` with the given arguments."""

    NAME = "GIT_ADD"
    DESCRIPTION = "Runs `git add` with the given arguments on the project repository."

    def __init__(self, project: VProject, *git_add_args: str) -> None:
        super().__init__(project)
        self.__git_add_args = git_add_args

    def __call__(self) -> StepResult:
        self.status = StepResult.OK
        try:
            git.add(Path(self.project.source_of_primary), *self.__git_add_args)
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: git add {' '.join(self.__git_add_args)}",
            " " * indent
        )


class GitCommit(ProjectStep):
    """Commits to the project repository."""

    NAME = "GIT_COMMIT"
    DESCRIPTION = "Commits to the project repository."

    def __init__(
        self,
        project: VProject,
        message: tp.Optional[str] = None,
        allow_empty: bool = False
    ) -> None:
        super().__init__(project)
        self.__message = message
        self.__allow_empty = allow_empty

    def __call__(self) -> StepResult:
        self.status = StepResult.OK
        try:
            git.commit(
                Path(self.project.source_of_primary), self.__message,
                self.__allow_empty
            )
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: git commit -m \"{self.__message}\"",
            " " * indent
        )


class GitCheckout(ProjectStep):
    """Checkout the project repository."""

    NAME = "GIT_CHECKOUT"
    DESCRIPTION = "Checkout a revision on the project repository."

    def __init__(self, project: VProject, commit: CommitHash) -> None:
        super().__init__(project)
        self.__commit = commit

    def __call__(self) -> StepResult:
        self.status = StepResult.OK
        try:
            git.checkout_branch_or_commit(
                Path(self.project.source_of_primary), self.__commit
            )
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        return textwrap.indent(
            f"* {self.project.name}: git checkout {self.__commit}", " " * indent
        )
