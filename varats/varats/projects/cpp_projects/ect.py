"""Project file for ECT."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.source import HTTP, HTTPUntar
from benchbuild.utils.cmd import make, cmake, mkdir
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap


class Ect(VProject):
    """
    Efficient Compression Tool (or ECT) is a C++ file optimizer.

    It supports PNG, JPEG, GZIP and ZIP files.
    """

    NAME = 'ect'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="ect",
            remote="https://github.com/danjujan/Efficient-Compression-Tool.git",
            local="ect",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        HTTP(
            local="archlinux.png",
            remote={
                "1.0":
                    "https://upload.wikimedia.org/wikipedia/"
                    "commons/e/e8/Archlinux-logo-standard-version.png"
            }
        ),
        HTTP(
            local="vara.jpg",
            remote={
                "1.0":
                    "https://upload.wikimedia.org/wikipedia/"
                    "commons/b/bc/VARA_speldje.JPG"
            }
        ),
        HTTP(
            local="ect.zip",
            remote={
                "1.0":
                    "https://github.com/fhanau/Efficient-Compression-Tool/"
                    "archive/refs/tags/v0.9.4.zip"
            }
        ),
        HTTP(
            local="ect.tar.gz",
            remote={
                "1.0":
                    "https://github.com/fhanau/Efficient-Compression-Tool/"
                    "archive/refs/tags/v0.9.4.tar.gz"
            }
        ),
        HTTPUntar(
            local="ect_src",
            remote={
                "1.0":
                    "https://github.com/fhanau/Efficient-Compression-Tool/"
                    "archive/refs/tags/v0.9.4.tar.gz"
            }
        ),
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'nasm', 'git', 'cmake', 'make')

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.JAN): [
            VCommand(
                SourceRoot("ect") / RSBinary("ect"),
                output_param=["{output}"],
                output=SourceRoot("archlinux.png"),
                creates=["archlinux.png"],
                consumes=["archlinux.png"],
                label="png-only",
            ),
            VCommand(
                SourceRoot("ect") / RSBinary("ect"),
                output_param=["{output}"],
                output=SourceRoot("vara.jpg"),
                creates=["vara.jpg"],
                consumes=["vara.jpg"],
                label="jpg-only",
            ),
            VCommand(
                SourceRoot("ect") / RSBinary("ect"),
                output_param=["{output}"],
                output=SourceRoot("ect.zip"),
                creates=["ect.zip"],
                consumes=["ect.zip"],
                label="zip-only",
            ),
            VCommand(
                SourceRoot("ect") / RSBinary("ect"),
                output_param=["{output}"],
                output=SourceRoot("ect.tar.gz"),
                creates=["ect.tar.gz"],
                consumes=["ect.tar.gz"],
                label="gzip-only",
            ),
            VCommand(
                SourceRoot("ect") / RSBinary("ect"),
                output_param=["{output}"],
                output=SourceRoot("ect_src"),
                creates=["ect_src.zip"],
                #consumes=["ect_src"],
                label="dir-only",
            ),
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Ect.NAME))

        binary_map.specify_binary(
            "build/ect", BinaryType.EXECUTABLE, valid_exit_codes=[0, 1]
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        ect_source = local.path(self.source_of_primary)

        cpp_compiler = bb.compiler.cxx(self)
        mkdir(ect_source / "build")
        with local.cwd(ect_source / "build"):
            with local.env(CXX=str(cpp_compiler)):
                bb.watch(cmake)("../src")

            bb.watch(make)()

        with local.cwd(ect_source):
            verify_binaries(self)
