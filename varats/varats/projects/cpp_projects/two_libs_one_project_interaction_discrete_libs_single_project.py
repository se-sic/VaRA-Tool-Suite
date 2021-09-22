"""Project implementation for the
TwoLibsOneProjectInteractionDiscreteLibsSingleProject library analysis
repository."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    VaraTestRepoSource,
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
    VaraTestRepoSubmodule,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class TwoLibsOneProjectInteractionDiscreteLibsSingleProject(VProject):
    """Class to analyse interactions between two discrete libraries and one
    project."""

    NAME = 'TwoLibsOneProjectInteractionDiscreteLibsSingleProject'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        VaraTestRepoSource(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/Elementalist",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        ),
        VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/fire_lib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        ),
        VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/water_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/water_lib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        ),
        VaraTestRepoSubmodule(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/earth_lib",
            local="TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            "/earth_lib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteractionDiscreteLibsSingleProject"
            )
        )
    ]

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return wrap_paths_to_binaries([(
            local.path("revision") /
            "build/test_prog/elementalist/elementalist", BinaryType.EXECUTABLE
        )])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        mkdir(version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)
