"""Project file for opencv."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class OpenCV(VProject):
    """Open Source Computer Vision Library."""

    NAME = 'opencv'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CPP_LIBRARY

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="opencv",
            remote="https://github.com/opencv/opencv.git",
            local="opencv",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'libgtk2.0-dev', 'pkg-config', 'libavcodec-dev',
        'libavformat-dev', 'libswscale-dev'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(OpenCV.NAME))

        binary_map.specify_binary(
            'build/lib/libopencv_core.so', BinaryType.SHARED_LIBRARY
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        opencv_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        build_folder = opencv_source / "build"
        build_folder.mkdir()
        with local.cwd(build_folder):

            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(opencv_source):
            verify_binaries(self)
