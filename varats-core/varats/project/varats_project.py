"""
VaRA-TS project abstraction.

This module defines the main project abstractions for VaRA-TS that extend the
benchbuild interface with tool suite specific functions.
"""
import typing as tp
from abc import abstractmethod

import benchbuild as bb

from varats.project.project_domain import ProjectDomains
from varats.project.project_util import ProjectBinaryWrapper
from varats.utils.git_util import ShortCommitHash


class VProject(bb.Project):  # type: ignore
    """VaRA-TS project abstraction, extending the interface which is required
    from benchbuild."""

    DOMAIN: ProjectDomains

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        return self.binaries_for_revision(
            ShortCommitHash(self.version_of_primary)
        )

    @staticmethod
    @abstractmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        """
        Return a list of binaries generated by the project, for the given
        revision.

        Args:
            revision: to determine the binaries for

        Returns:
            list of project binaries
        """
