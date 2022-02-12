import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class VCSTestBasic01(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestBasic01"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestBasic01",
            remote="VCSAnalysisRepos/Basic01",
            local="VCSTestBasic01",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        basic_01_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(basic_01_version_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)


class VCSTestBasic02(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestBasic02"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestBasic02",
            remote="VCSAnalysisRepos/Basic02",
            local="VCSTestBasic02",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        basic_02_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(basic_02_version_source):
            bb.watch(c_compiler
                    )("main.c", "-Wl,--warn-unresolved-symbols", "-o", "main")

            verify_binaries(self)


class VCSTestBasic03(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestBasic03"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestBasic03",
            remote="VCSAnalysisRepos/Basic03",
            local="VCSTestBasic03",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        basic_03_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(basic_03_version_source):
            bb.watch(c_compiler
                    )("main.c", "-Wl,--warn-unresolved-symbols", "-o", "main")

            verify_binaries(self)


class VCSTestBasic04(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestBasic04"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestBasic04",
            remote="VCSAnalysisRepos/Basic04",
            local="VCSTestBasic04",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        basic_04_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(basic_04_version_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)


class VCSTestBasic05(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestBasic05"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestBasic05",
            remote="VCSAnalysisRepos/Basic05",
            local="VCSTestBasic05",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        basic_05_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(basic_05_version_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)


class VCSTestCall01(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestCall01"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestCall01",
            remote="VCSAnalysisRepos/Call01",
            local="VCSTestCall01",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        call_01_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(call_01_version_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)


class VCSTestDeletionWithInteraction(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestDeletionWithInteraction"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestDeletionWithInteraction",
            remote="VCSAnalysisRepos/DeletionWithInteraction",
            local="VCSTestDeletionWithInteraction",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        del_with_inter_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(del_with_inter_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)


class VCSTestDeletionWithoutInteraction(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestDeletionWithoutInteraction"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestDeletionWithoutInteraction",
            remote="VCSAnalysisRepos/DeletionWithoutInteraction",
            local="VCSTestDeletionWithoutInteraction",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        del_without_inter_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(del_without_inter_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)


class VCSTestMergeExample01(VProject):
    """Test scenario for the incremental analysis."""

    NAME = "VCSTestMergeExample01"
    GROUP = "test_projects"
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            project_name="VCSTestMergeExample01",
            remote="VCSAnalysisRepos/MergeExample01",
            local="VCSTestMergeExample01",
            refspec="HEAD",
            limit=None,
            shallow=False
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([("main", BinaryType.EXECUTABLE)])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        merge_example_01_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)

        with local.cwd(merge_example_01_source):
            bb.watch(c_compiler)("main.c", "-o", "main")

            verify_binaries(self)
