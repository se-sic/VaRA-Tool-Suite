"""Project file for TwoLibsOneProjectInteraction_DiscreteLibs_SingleProject."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, cp, git, make, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.paper_mgmt.paper_config import project_filter_generator
from varats.project.project_util import (
    VaraTestRepoSource,
    ProjectBinaryWrapper,
    wrap_paths_to_binaries,
    BinaryType,
)
from varats.utils.settings import bb_cfg


class TwoLibsOneProjectInteraction_DiscreteLibs_SingleProject(
    bb.Project  # type: ignore
):
    """Class to analyse interactions between two discrete libraries and one
    project."""

    NAME = 'TwoLibsOneProjectInteraction_DiscreteLibs_SingleProject'
    GROUP = 'cpp_projects'
    DOMAIN = 'library-testproject'

    SOURCE = [
        VaraTestRepoSource(
            remote="LibraryAnalysisRepos"
            "/TwoLibsOneProjectInteraction_DiscreteLibs_SingleProject"
            "/Elementalist",
            local="TwoLibsOneProjectInteraction_DiscreteLibs_SingleProject"
            "/Elementalist",
            refspec="HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator(
                "TwoLibsOneProjectInteraction_DiscreteLibs_SingleProject"
            )
        )
    ]

    @property
    def binaries(self) -> tp.List[ProjectBinaryWrapper]:
        """Return a list of binaries generated by the project."""
        version_source = local.path(self.source_of_primary)

        return wrap_paths_to_binaries([(
            version_source / "build/test_prog/elementalist/elementalist",
            BinaryType.executable
        )])

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Contains instructions on how to build the project."""

        version_source = local.path(self.source_of_primary)
        c_compiler = bb.compiler.cc(self)  # type: ignore
        cxx_compiler = bb.compiler.cxx(self)  # type: ignore
        mkdir(version_source / "build")

        # As long as multiple VaraTestRepoSources are not working, one has to
        # ensure that the necessary libs are located as git repositories in the
        # benchbuild/tmp dir

        path_to_libs_in_tmp = version_source / "../../../../../tmp"
        path_to_root_dir = version_source / "../"

        cp("-r", path_to_libs_in_tmp / "fire_lib", path_to_root_dir)
        cp("-r", path_to_libs_in_tmp / "water_lib", path_to_root_dir)

        with local.cwd(version_source):
            git("submodule", "sync")
            git("submodule", "update")

        with local.cwd(version_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("-G", "Unix Makefiles", "..")  # type: ignore
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))  # type: ignore
