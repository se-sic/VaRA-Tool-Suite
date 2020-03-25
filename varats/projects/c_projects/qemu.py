"""
Project file for qemu.
"""
import typing as tp
from pathlib import Path

from benchbuild.settings import CFG as BB_CFG
from benchbuild.utils.compiler import cc, cxx
from benchbuild.utils.run import run
from benchbuild.project import Project
from benchbuild.utils.cmd import make
from benchbuild.utils.download import with_git

from plumbum import local

from varats.data.provider.cve.cve_provider import CVEProviderHook
from varats.paper.paper_config import project_filter_generator
from varats.utils.project_util import wrap_paths_to_binaries


@with_git("https://github.com/qemu/qemu.git",
          refspec="HEAD",
          shallow_clone=False,
          version_filter=project_filter_generator("qemu"))
class Qemu(Project, CVEProviderHook):  # type: ignore
    """QEMU, the FAST! processor emulator."""

    NAME = 'qemu'
    GROUP = 'c_projects'
    DOMAIN = 'Hardware emulator'
    VERSION = 'HEAD'

    SRC_FILE = NAME + "-{0}".format(VERSION)

    @property
    def binaries(self) -> tp.List[Path]:
        """Return a list of binaries generated by the project."""
        return wrap_paths_to_binaries(
            ["build/x86_64-softmmu/qemu-system-x86_64"])

    def run_tests(self, runner: run) -> None:
        pass

    def compile(self) -> None:
        self.download()

        self.cflags += ['-Wno-tautological-type-limit-compare']

        c_compiler = cc(self)
        cxx_compiler = cxx(self)
        build_folder = local.path(self.SRC_FILE + "/" + "build")
        build_folder.mkdir()

        with local.cwd(build_folder):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                run(local["../configure"]
                    ["--disable-debug-info", "--target-list=x86_64-softmmu"])
                run(make["-j", int(BB_CFG["jobs"])])

    def get_cve_product_info(self) -> tp.Tuple[str, str]:
        return "qemu", "qemu"
