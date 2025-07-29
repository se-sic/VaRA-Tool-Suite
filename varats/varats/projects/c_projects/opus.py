"""Project file for opus."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.source import HTTP, HTTPUntar
from benchbuild.utils.cmd import make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    RSBinary,
    WorkloadCategory,
    ConfigParams,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_repo,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import bb_cfg


class Opus(VProject):
    """Opus is a codec for interactive speech and audio transmission over the
    Internet."""

    NAME = 'opus'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.CODEC

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="opus",
            remote="https://github.com/xiph/opus.git",
            local="opus",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_10
    ).run('apt', 'install', '-y', 'autoconf', 'automake', 'libtool')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(Opus.NAME))

        binary_map.specify_binary(".libs/libopus.so", BinaryType.SHARED_LIBRARY)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        opus_source = local.path(self.source_of_primary)

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)
        with local.cwd(opus_source):
            with local.env(CC=str(clang)):
                bb.watch(local["./autogen.sh"])()
                bb.watch(local["./configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("opus-codec", "opus")]


class OpusTools(VProject):
    NAME = "OpusTools"
    GROUP = "c_projects"
    DOMAIN = ProjectDomains.CODEC

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="OpusTools",
            remote="https://github.com/xiph/opus-tools.git",
            local="OpusTools",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        HTTPUntar(
            local="trondheim.wav",
            remote={
                "1.0":
                    "https://www.phoronix-test-suite.com/benchmark-files/pts-trondheim-wav-3.tar.gz"
            }
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.SMALL): [
            VCommand(
                SourceRoot("OpusTools") / RSBinary("opusenc"),
                ConfigParams(),
                "trondheim.wav/pts-trondheim-3.wav",
                "trondheim.opus",
                label="trondheim"
            )
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_repo(OpusTools.NAME))

        binary_map.specify_binary("build/opusenc", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        opus_source = local.path(self.source_of_primary)
        build_dir = opus_source / "build"
        build_dir.mkdir(parents=True, exist_ok=True)

        self.cflags += ["-fPIC"]

        clang = bb.compiler.cc(self)

        with local.cwd(build_dir):
            with local.env(CC=str(clang)):
                bb.watch(local["../autogen.sh"])()
                bb.watch(local["../configure"]
                        )("--without-flac", "--with-gnu-ld=yes")
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    def recompile(self):
        """Compile the project."""
        opus_source = local.path(self.source_of_primary)

        with local.cwd(opus_source / "build"):
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
