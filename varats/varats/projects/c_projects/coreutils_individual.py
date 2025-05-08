"""GNU coreutils as individual projects."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.utils.cmd import git, make
from benchbuild.utils.settings import get_number_of_jobs
from containers.containers import get_base_image, ImageBase
from plumbum import local

from varats.experiment.workload_util import (
    WorkloadCategory,
    RSBinary,
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

if tp.TYPE_CHECKING:
    from benchbuild.project import Sources


def _coreutils_source(tool_name: str) -> 'Sources':
    return [
        PaperConfigSpecificGit(
            project_name=tool_name,
            remote="https://github.com/coreutils/coreutils.git",
            local="coreutils",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            submodule_set_urls={
                "gnulib": "https://github.com/coreutils/gnulib"
            }
        ),
        FeatureSource()
    ]


def _coreutils_binary_map(tool_name: str) -> RevisionBinaryMap:
    return RevisionBinaryMap(
        get_local_project_repo(CoreutilsSort.NAME)
    ).specify_binary(f'src/{tool_name}', BinaryType.EXECUTABLE)


def _coreutils_run_tests(project: VProject) -> None:
    coreutils_source = local.path(project.source_of_primary)
    with local.cwd(coreutils_source):
        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()), "check")


def _coreutils_compile(project: VProject) -> None:
    coreutils_source = local.path(project.source_of_primary)
    compiler = bb.compiler.cc(project)
    with local.cwd(coreutils_source):
        git("submodule", "init")
        git("submodule", "update")
        with local.env(CC=str(compiler)):
            bb.watch(local["./bootstrap"])()
            bb.watch(local["./configure"])("--disable-gcc-warnings")

        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

        verify_binaries(project)


class CoreutilsSort(VProject):
    """GNU coreutils - sort"""

    NAME = "coreutils_sort"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/sort.xml"

    SOURCE = _coreutils_source(NAME)
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("sort"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = get_base_image(ImageBase.DEBIAN_12)

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("sort")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)
