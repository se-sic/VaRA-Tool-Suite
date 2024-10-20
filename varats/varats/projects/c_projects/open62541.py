"""Project file for open62541."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import cmake, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import ImageBase, get_base_image
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    RevisionBinaryMap,
    get_local_project_repo,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Open62541(VProject):
    """open62541 (http://open62541.org) is an open source implementation of OPC
    UA (OPC Unified Architecture / IEC 62541) written in the C language."""

    NAME = 'open62541'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.ARCHITECTURE

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='open62541',
            remote="https://github.com/open62541/open62541.git",
            local="open62541",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', "git", "build-essential", "pkg-config", "cmake",
        "python3"
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Open62541.NAME))

        binary_map.specify_binary(
            'build/bin/libopen62541.a', BinaryType.STATIC_LIBRARY
        )

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        open62541_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        build_folder = open62541_version_source / "build"
        build_folder.mkdir()

        with local.cwd(build_folder):
            with local.env(CC=str(c_compiler)):
                bb.watch(cmake)("..")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(open62541_version_source):
            verify_binaries(self)
