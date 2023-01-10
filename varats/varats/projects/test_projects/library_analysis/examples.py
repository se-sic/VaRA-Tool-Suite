"""Library interaction example projects."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    get_local_project_git_path,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class Context(VProject):
    """Scenario where interaction can be explained by context node."""

    NAME = 'context'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="context",
            remote="LibraryAnalysisRepos/examples/context/context",
            local="context",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Context.NAME))
        binary_map.specify_binary("build/context", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class GlobalState(VProject):
    """Hidden interaction caused by global state."""

    NAME = 'global_state'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="global_state",
            remote="LibraryAnalysisRepos/examples/global_state/global_state",
            local="global_state",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(GlobalState.NAME)
        )
        binary_map.specify_binary("build/globals", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class NewInteractions(VProject):
    """Hidden interaction introduces new interactions."""

    NAME = 'new_interactions'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="new_interactions",
            remote=
            "LibraryAnalysisRepos/examples/new_interactions/new_interactions",
            local="new_interactions",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(NewInteractions.NAME)
        )
        binary_map.specify_binary(
            "build/new_interactions", BinaryType.EXECUTABLE
        )
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class Overloading(VProject):
    """Hidden interaction caused by function overloading."""

    NAME = 'overloading'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="overloading",
            remote="LibraryAnalysisRepos/examples/overloading/overloading",
            local="overloading",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Overloading.NAME)
        )
        binary_map.specify_binary("build/overloading", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class Overriding(VProject):
    """Hidden interaction caused by subtyping/function overriding."""

    NAME = 'overriding'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="overriding",
            remote="LibraryAnalysisRepos/examples/overriding/overriding",
            local="overriding",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Overriding.NAME)
        )
        binary_map.specify_binary("build/overriding", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class Refactoring(VProject):
    """Refactoring changes interactions."""

    NAME = 'refactoring'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="refactoring",
            remote="LibraryAnalysisRepos/examples/refactoring/refactoring",
            local="refactoring",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Refactoring.NAME)
        )
        binary_map.specify_binary("build/refactoring", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class Refactoring2(VProject):
    """Refactoring that does not change interactions."""

    NAME = 'refactoring2'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="refactoring2",
            remote="LibraryAnalysisRepos/examples/refactoring2/refactoring2",
            local="refactoring2",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Refactoring2.NAME)
        )
        binary_map.specify_binary("build/refactoring", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class Templates(VProject):
    """Hidden interaction caused by template specialization."""

    NAME = 'templates'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="templates",
            remote="LibraryAnalysisRepos/examples/templates/templates",
            local="templates",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Templates.NAME)
        )
        binary_map.specify_binary("build/templates", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)


class Unrelated(VProject):
    """Hidden interaction caused by template specialization."""

    NAME = 'unrelated'
    GROUP = 'library_analysis'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="unrelated",
            remote="LibraryAnalysisRepos/examples/unrelated/unrelated",
            local="unrelated",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(Unrelated.NAME)
        )
        binary_map.specify_binary("build/unrelated", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)
