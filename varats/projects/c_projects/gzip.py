"""
Project file for gzip.
"""
import re

from benchbuild.settings import CFG
from benchbuild.utils.cmd import make
from benchbuild.utils.compiler import cc
from benchbuild.utils.download import with_git
from benchbuild.utils.run import run
import benchbuild.project as prj

from plumbum import local
import typing as tp

from varats.paper.case_study import ReleaseType, ReleaseProvider
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import get_tagged_commits


@with_git(
    "https://git.savannah.gnu.org/git/gzip.git",
    limit=200,
    refspec="HEAD",
    shallow_clone=False,
    version_filter=project_filter_generator("gzip"))
class Gzip(prj.Project, ReleaseProvider):  # type: ignore
    """ Compression and decompression tool Gzip (fetched by Git) """

    NAME = 'gzip'
    GROUP = 'c_projects'
    DOMAIN = 'compression'
    VERSION = 'HEAD'

    BIN_NAMES = ['gzip']
    SRC_FILE = NAME + "-{0}".format(VERSION)

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
            run(make["-j", int(CFG["jobs"])])

    @classmethod
    def get_release_revisions(cls, release_type: ReleaseType) -> tp.List[str]:
        major_release_regex = "^v[0-9]+\\.[0-9]+$"
        minor_release_regex = "^v[0-9]+\\.[0-9]+\\.[0-9]+$"

        tagged_commits = get_tagged_commits(cls.NAME)
        if release_type == ReleaseType.major:
            return [
                h for h, tag in tagged_commits
                if re.match(major_release_regex, tag)
            ]
        else:
            return [
                h for h, tag in tagged_commits
                if re.match(minor_release_regex, tag)
            ]
