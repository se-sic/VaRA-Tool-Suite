"""
Project file for gzip.
"""
from plumbum import local
from benchbuild.settings import CFG
from benchbuild.utils.compiler import cc
from benchbuild.utils.run import run
import benchbuild.project as prj
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from varats.paper.paper_config import project_filter_generator


def filter_func(version):
    """
    Example filter function.
    TODO: remove
    """
    new = [
        "fa0feec",
        "3557cd5",
    ]
    good = ["20540be",
            "8aa53f1",
            "a604573",
            "e48a916",
            "8ebed06",
            "d2e7cf9",
            "9c2a2de",
            "62e1b9e",
            ]
    bad = ["63aa226",
           "30cc414",
           "5671fac",
           ]
    return True


@with_git(
    "https://git.savannah.gnu.org/git/gzip.git",
    limit=100,
    refspec="HEAD",
    version_filter=project_filter_generator("gzip"))
class Gzip(prj.Project):
    """ Compression and decompression tool Gzip (fetched by Git) """

    NAME = 'gzip'
    GROUP = 'git'
    DOMAIN = 'version control'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    def run_tests(self, runner):
        pass

    def compile(self):
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
