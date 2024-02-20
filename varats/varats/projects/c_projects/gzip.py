"""Project file for gzip."""
import re
import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple, HTTPUntar
from benchbuild.utils.cmd import make, mkdir
from benchbuild.utils.revision_ranges import block_revisions, RevisionRange
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import (
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
        ),
        HTTPMultiple(
            local="geo-maps",
            remote={
                "1.0":
                    "https://github.com/simonepri/geo-maps/releases/"
                    "download/v0.6.0"
            },
            files=["countries-land-1km.geo.json", "countries-land-1m.geo.json"]
        ),
        HTTPUntar(
            local="cantrbry.tar.gz",
            remote={
                "1.0":
                    "http://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
            }
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt', 'install', '-y', 'autoconf', 'automake', 'libtool', 'autopoint',
        'gettext', 'texinfo', 'rsync'
    )

    files = ["alice29.txt", "asyoulik.txt", "cp.html", "fields.c", "grammar.lsp", 
             "kennedy.xls", "lcet10.txt", "plrabn12.txt", "ptt5", "sum", "xargs.1"]
    
    configs = [
        ["-1"],
        ["-5"],
        ["-3"],
        ["-9"],
        ["-7"],
        ["--recursive", "-1"],
        ["--recursive", "-5"],
        ["--recursive", "-3"],
        ["--recursive", "-9"],
        ["--recursive", "-7"],
        ["--verbose", "-1"],
        ["--verbose", "-5"],
        ["--verbose", "-3"],
        ["--verbose", "-9"],
        ["--verbose", "-7"],
        ["--quiet", "-1"],
        ["--quiet", "-5"],
        ["--quiet", "-3"],
        ["--quiet", "-9"],
        ["--quiet", "-7"],
        ["-S", "-1"],
        ["-S", "-5"],
        ["-S", "-3"],
        ["-S", "-9"],
        ["-S", "-7"],
        ["--test", "-1"],
        ["--test", "-5"],
        ["--test", "-3"],
        ["--test", "-9"],
        ["--test", "-7"],
        ["--recursive", "--verbose", "-1"],
        ["--recursive", "--verbose", "-5"],
        ["--recursive", "--verbose", "-3"],
        ["--recursive", "--verbose", "-9"],
        ["--recursive", "--verbose", "-7"],
        ["--recursive", "--quiet", "-1"],
        ["--recursive", "--quiet", "-5"],
        ["--recursive", "--quiet", "-3"],
        ["--recursive", "--quiet", "-9"],
        ["--recursive", "--quiet", "-7"],
        ["--recursive", "-S", "-1"],
        ["--recursive", "-S", "-5"],
        ["--recursive", "-S", "-3"],
        ["--recursive", "-S", "-9"],
        ["--recursive", "-S", "-7"],
        ["--recursive", "--test", "-1"],
        ["--recursive", "--test", "-5"],
        ["--recursive", "--test", "-3"],
        ["--recursive", "--test", "-9"],
        ["--recursive", "--test", "-7"],
        ["--verbose", "--quiet", "-1"],
        ["--verbose", "--quiet", "-5"],
        ["--verbose", "--quiet", "-3"],
        ["--verbose", "--quiet", "-9"],
        ["--verbose", "--quiet", "-7"],
        ["--verbose", "-S", "-1"],
        ["--verbose", "-S", "-5"],
        ["--verbose", "-S", "-3"],
        ["--verbose", "-S", "-9"],
        ["--verbose", "-S", "-7"],
        ["--verbose", "--test", "-1"],
        ["--verbose", "--test", "-5"],
        ["--verbose", "--test", "-3"],
        ["--verbose", "--test", "-9"],
        ["--verbose", "--test", "-7"],
        ["--quiet", "-S", "-1"],
        ["--quiet", "-S", "-5"],
        ["--quiet", "-S", "-3"],
        ["--quiet", "-S", "-9"],
        ["--quiet", "-S", "-7"],
        ["--quiet", "--test", "-1"],
        ["--quiet", "--test", "-5"],
        ["--quiet", "--test", "-3"],
        ["--quiet", "--test", "-9"],
        ["--quiet", "--test", "-7"],
        ["-S", "--test", "-1"],
        ["-S", "--test", "-5"],
        ["-S", "--test", "-3"],
        ["-S", "--test", "-9"],
        ["-S", "--test", "-7"],
        ["--recursive", "--verbose", "--quiet", "-S", "--test", "-1"],
        ["--recursive", "--verbose", "--quiet", "-S", "--test", "-5"],
        ["--recursive", "--verbose", "--quiet", "-S", "--test", "-3"],
        ["--recursive", "--verbose", "--quiet", "-S", "--test", "-9"],
        ["--recursive", "--verbose", "--quiet", "-S", "--test", "-7"],
        ["--verbose", "--quiet", "-S", "--test", "-1"],
        ["--verbose", "--quiet", "-S", "--test", "-5"],
        ["--verbose", "--quiet", "-S", "--test", "-3"],
        ["--verbose", "--quiet", "-S", "--test", "-9"],
        ["--verbose", "--quiet", "-S", "--test", "-7"],
        ["--recursive", "--quiet", "-S", "--test", "-1"],
        ["--recursive", "--quiet", "-S", "--test", "-5"],
        ["--recursive", "--quiet", "-S", "--test", "-3"],
        ["--recursive", "--quiet", "-S", "--test", "-9"],
        ["--recursive", "--quiet", "-S", "--test", "-7"],
        ["--recursive", "--verbose", "-S", "--test", "-1"],
        ["--recursive", "--verbose", "-S", "--test", "-5"],
        ["--recursive", "--verbose", "-S", "--test", "-3"],
        ["--recursive", "--verbose", "-S", "--test", "-9"],
        ["--recursive", "--verbose", "-S", "--test", "-7"],
        ["--recursive", "--verbose", "--quiet", "--test", "-1"],
        ["--recursive", "--verbose", "--quiet", "--test", "-5"],
        ["--recursive", "--verbose", "--quiet", "--test", "-3"],
        ["--recursive", "--verbose", "--quiet", "--test", "-9"],
        ["--recursive", "--verbose", "--quiet", "--test", "-7"],
        ["--recursive", "--verbose", "--quiet", "-S", "-1"],
        ["--recursive", "--verbose", "--quiet", "-S", "-5"],
        ["--recursive", "--verbose", "--quiet", "-S", "-3"],
        ["--recursive", "--verbose", "--quiet", "-S", "-9"],
        ["--recursive", "--verbose", "--quiet", "-S", "-7"]
    ]
    
    commands = []


    for file in files:
        for i, config in enumerate(configs):
            command = None
            command = Command(
                SourceRoot("gzip") / RSBinary("gzip"),
                *config,
                "--force",  # needed because BB creates symlinks for the inputs
                "--keep", # needed for repeating with the same workload
                "cantrbry.tar.gz/" + file,
                label=file + "-config" + "{:04d}".format(i),
                creates=["cantrbry.tar.gz/" + file + ".gz"]
            )
            
            
            commands.append(command)

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): commands,
        WorkloadSet(WorkloadCategory.SMALL): [
            Command(
                SourceRoot("gzip") / RSBinary("gzip"),
                "-k",
                "--force",  # needed because BB creates symlinks for the inputs
                "geo-maps/countries-land-1km.geo.json",
                label="countries-land-1km",
                creates=["geo-maps/countries-land-1km.geo.json.gz"]
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            Command(
                SourceRoot("gzip") / RSBinary("gzip"),
                "--keep",
                "--name",
                "--verbose",
                "--best",
                "--force",  # needed because BB creates symlinks for the inputs
                "geo-maps/countries-land-1m.geo.json",
                label="geo-maps/countries-land-1m",
                creates=["geo-maps/countries-land-1m.geo.json.gz"]
            )
        ],
    }

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

        # Build binaries in separate dir because executing the binary with path
        # 'gzip' will execute '/usr/bin/gzip' independent of the current working
        # directory.
        mkdir("-p", gzip_version_source / "build")

        self.cflags += [
            "-Wno-error=string-plus-int", "-Wno-error=shift-negative-value",
            "-Wno-string-plus-int", "-Wno-shift-negative-value"
        ]

        with local.cwd(gzip_version_source):
            bb.watch(local["./bootstrap"])()

        c_compiler = bb.compiler.cc(self)
        with local.cwd(gzip_version_source / "build"
                      ), local.env(CC=str(c_compiler)):
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
