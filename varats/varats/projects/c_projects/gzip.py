"""Project file for gzip."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, mkdir
from benchbuild.utils.revision_ranges import block_revisions, RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper_mgmt.paper_config import (
    PaperConfigSpecificGit,
    project_filter_generator,
)
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    get_tagged_commits,
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.git_util import (
    FullCommitHash,
    ShortCommitHash,
    RevisionBinaryMap,
)
from varats.utils.settings import bb_cfg


class Gzip(VProject, ReleaseProviderHook):
    """Compression and decompression tool Gzip (fetched by Git)"""

    NAME = 'gzip'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.COMPRESSION

    SOURCE = [
        block_revisions([
            # TODO (se-sic/VaRA#537): glibc < 2.28
            # see e.g. https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=915151
            RevisionRange(
                "6ef28aeb035af20818578b1a1bc537f797c27029",
                "203e40cc4558a80998d05eb74b373a51e796ca8b", "Needs glibc < 2.28"
            )
        ])(
            PaperConfigSpecificGit(
                project_name="gzip",
                remote="https://github.com/vulder/gzip.git",
                local="gzip",
                refspec="origin/HEAD",
                limit=None,
                shallow=False
            )
        ),
        bb.source.GitSubmodule(
            remote="https://github.com/coreutils/gnulib.git",
            local="gzip/gnulib",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("gzip")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'libtool', 'autopoint',
        'gettext', 'texinfo', 'rsync'
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(Gzip.NAME))

        binary_map.specify_binary("build/gzip", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        gzip_version_source = local.path(self.source_of_primary)

        # Build binaries in separate dir because executing the binary with path 'gzip' will execute '/usr/bin/gzip' independent of the current working directory.
        mkdir("-p", gzip_version_source / "build")

        self.cflags += [
            "-Wno-error=string-plus-int", "-Wno-error=shift-negative-value",
            "-Wno-string-plus-int", "-Wno-shift-negative-value"
        ]

        with local.cwd(gzip_version_source):
            bb.watch(local["./bootstrap"])()

        clang = bb.compiler.cc(self)
        with local.cwd(gzip_version_source / "build"), local.env(CC=str(clang)):
            bb.watch(local["../configure"])()
            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(gzip_version_source):
            verify_binaries(self)

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        major_release_regex = "^v[0-9]+\\.[0-9]+$"
        minor_release_regex = "^v[0-9]+\\.[0-9]+(\\.[0-9]+)?$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.MAJOR:
            return [(FullCommitHash(h), tag)
                    for h, tag in tagged_commits
                    if re.match(major_release_regex, tag)]
        return [(FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match(minor_release_regex, tag)]

    @classmethod
    def get_cve_product_info(cls) -> tp.List[tp.Tuple[str, str]]:
        return [("gzip", "gzip"), ("gnu", "gzip")]
