"""
Project file for gzip.
"""
import typing as tp
from pathlib import Path
import re

from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.case_study import ReleaseType, ReleaseProvider
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import get_tagged_commits, \
    wrap_paths_to_binaries, BlockedRevisionRange, block_revisions


@block_revisions([
    # TODO (se-passau/VaRA#537): glibc < 2.28
    # see e.g. https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=915151
    BlockedRevisionRange("6ef28aeb035af20818578b1a1bc537f797c27029",
                         "203e40cc4558a80998d05eb74b373a51e796ca8b",
                         "Needs glibc < 2.28")
])
@with_git(
    "https://git.savannah.gnu.org/git/gzip.git",
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("gzip"))
class Gzip(prj.Project, ReleaseProvider, CVEProviderHook):  # type: ignore
    """ Compression and decompression tool Gzip (fetched by Git) """

    NAME = 'gzip'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(["gzip"])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += [
            "-Wno-error=string-plus-int", "-Wno-error=shift-negative-value",
            "-Wno-string-plus-int", "-Wno-shift-negative-value"
        ]

        clang = cc(self)
        with local.cwd(self.SRC_FILE):
            with local.env(CC=str(clang)):
                run(local["./bootstrap"])
                run(local["./configure"])
            run(make["-j", int(BB_CFG["jobs"])])

    @classmethod
    def get_release_revisions(cls, release_type: ReleaseType) -> tp.List[str]:
        major_release_regex = "^v[0-9]+\\.[0-9]+$"
        minor_release_regex = "^v[0-9]+\\.[0-9]+(\\.[0-9]+)?$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.major:
            return [
                h for h, tag in tagged_commits
                if re.match(major_release_regex, tag)
            ]
        return [
            h for h, tag in tagged_commits
            if re.match(minor_release_regex, tag)
        ]

    def get_cve_product_info(self) -> tp.Tuple[str, str]:
        return "gnu", "gzip"

