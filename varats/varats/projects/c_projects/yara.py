"""Project file for yara."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make
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


class Yara(VProject):
    """
    YARA is a tool aimed at (but not limited to) helping malware researchers to
    identify and classify malware samples.

    With YARA you can create descriptions of malware families (or whatever you
    want to describe) based on textual or binary patterns.
    """

    NAME = 'yara'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.MALWARE_ANALYSIS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name='yara',
            remote="https://github.com/VirusTotal/yara.git",
            local="yara",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'autopoint', 'automake',
        'autotools-dev', 'make', 'pkg-config'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Yara.NAME))

        binary_map.specify_binary('yara', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        yara_version_source = local.path(self.source_of_primary)

        c_compiler = bb.compiler.cc(self)
        with local.cwd(yara_version_source):
            with local.env(CC=str(c_compiler)):
                bb.watch(local["./bootstrap.sh"])()
                bb.watch(local["./configure"])()

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)
