"""Git related project steps."""

import logging
import textwrap
from pathlib import Path

from benchbuild.utils.actions import ProjectStep, StepResult
from plumbum import ProcessExecutionError

import varats.utils.git_commands as git
from varats.project.varats_project import VProject
from varats.utils.git_util import CommitHash, RepositoryHandle

LOG = logging.Logger(__name__)


class GitAdd(ProjectStep):
    """Runs `git add` with the given arguments."""

    NAME = "GIT_ADD"
    DESCRIPTION = (
        "Runs `git add` with the given arguments on the project repository."
    )

    def __init__(self, project: VProject, *git_add_args: str) -> None:
        """Creates a step that runs `git add` with the given arguments."""
        super().__init__(project)
        self.__git_add_args = git_add_args

    def __call__(self) -> StepResult:
        """Runs the step."""
        self.status = StepResult.OK
        try:
            git.add(
                RepositoryHandle(Path(self.project.source_of_primary)),
                *self.__git_add_args,
            )
        except ProcessExecutionError:
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        """Returns a textual representation of the step."""
        return textwrap.indent(
            f"* {self.project.name}: git add {' '.join(self.__git_add_args)}",
            " " * indent,
        )


class GitCommit(ProjectStep):
    """Commits to the project repository."""

    NAME = "GIT_COMMIT"
    DESCRIPTION = "Commits to the project repository."

    def __init__(
        self,
        project: VProject,
        message: str | None = None,
        allow_empty: bool = False,
        no_verify: bool = False,
    ) -> None:
        """
        Creates a step that commits to the project repository.

        Args:
            project: the project to commit to
            message: the commit message
            allow_empty: whether to allow empty commits
            no_verify: whether to skip git hooks
        """
        super().__init__(project)
        self.__message = message
        self.__allow_empty = allow_empty
        self.__no_verify = no_verify

    def __call__(self) -> StepResult:
        """Runs the step."""
        self.status = StepResult.OK
        try:
            git.commit(
                RepositoryHandle(Path(self.project.source_of_primary)),
                self.__message,
                self.__allow_empty,
                self.__no_verify,
            )
        except ProcessExecutionError as e:
            LOG.error(e)
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        """Returns a textual representation of the step."""
        return textwrap.indent(
            f"* {self.project.name}: git commit -m \"{self.__message}\"",
            " " * indent,
        )


class GitCheckout(ProjectStep):
    """Checkout the project repository."""

    NAME = "GIT_CHECKOUT"
    DESCRIPTION = "Checkout a revision on the project repository."

    def __init__(self, project: VProject, commit: CommitHash) -> None:
        """Creates a step that checks out the given commit."""
        super().__init__(project)
        self.__commit = commit

    def __call__(self) -> StepResult:
        """Runs the step."""
        self.status = StepResult.OK
        try:
            git.checkout_branch_or_commit(
                RepositoryHandle(Path(self.project.source_of_primary)),
                self.__commit,
            )
        except ProcessExecutionError as e:
            LOG.error(e)
            self.status = StepResult.ERROR

        return self.status

    def __str__(self, indent: int = 0) -> str:
        """Returns a textual representation of the step."""
        return textwrap.indent(
            f"* {self.project.name}: git checkout {self.__commit}", " " * indent
        )
