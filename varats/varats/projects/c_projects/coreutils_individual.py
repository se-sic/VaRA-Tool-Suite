"""GNU coreutils as individual projects."""
import typing as tp

import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot
from benchbuild.source import HTTPMultiple
from benchbuild.utils.cmd import git, make
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
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
    from benchbuild.environments.domain.declarative import ContainerImage
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
        FeatureSource(),
        HTTPMultiple(
            local="coreutils-workloads",
            remote={
                "1.0":
                    "https://github.com/se-sic/coreutils-workloads/releases/download/v0.1"
            },
            files=[
                "jrc-en-full.xml",
                "random_data.txt",
            ]
        )
    ]


def _coreutils_container() -> 'ContainerImage':
    return get_base_image(ImageBase.DEBIAN_12).run(
        "apt", "install", "-y", "autoconf", "automake", "bison", "gettext",
        "gperf", "gzip", "help2man", "m4", "make", "perl", "tar", "texinfo",
        "wget", "xz-utils"
    )


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


class CoreutilsBasenc(VProject):
    """GNU coreutils - basenc"""

    NAME = "coreutils_basenc"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/basenc.xml"

    SOURCE = _coreutils_source(NAME)
    # TODO
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("basenc"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("basenc")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsCksum(VProject):
    """GNU coreutils - cksum"""

    NAME = "coreutils_cksum"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/cksum.xml"

    SOURCE = _coreutils_source(NAME)
    # TODO
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("cksum"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("cksum")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsDd(VProject):
    """GNU coreutils - dd"""

    NAME = "coreutils_dd"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/dd.xml"

    SOURCE = _coreutils_source(NAME)
    # TODO
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("dd"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("dd")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsFmt(VProject):
    """GNU coreutils - fmt"""

    NAME = "coreutils_fmt"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/fmt.xml"

    SOURCE = _coreutils_source(NAME)
    # TODO
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("fmt"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("fmt")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsOd(VProject):
    """GNU coreutils - od"""

    NAME = "coreutils_od"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/od.xml"

    SOURCE = _coreutils_source(NAME)
    # TODO
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("od"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("od")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsPr(VProject):
    """GNU coreutils - pr"""

    NAME = "coreutils_pr"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/pr.xml"

    SOURCE = _coreutils_source(NAME)
    # TODO
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("pr"),
                ConfigParams(),
                "/local/storage/boehmseb/coreutils-test-inputs/sort/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("pr")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsSort(VProject):
    """GNU coreutils - sort"""

    NAME = "coreutils_sort"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/sort.xml"

    SOURCE = _coreutils_source(NAME)
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("sort"),
                ConfigParams(),
                "coreutils-workloads/random_data.txt",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("sort")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsUniq(VProject):
    """GNU coreutils - uniq"""

    NAME = "coreutils_uniq"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/uniq.xml"

    SOURCE = _coreutils_source(NAME)
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("uniq"),
                ConfigParams(),
                "coreutils-workloads/jrc-en-full.xml",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("uniq")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)


class CoreutilsWc(VProject):
    """GNU coreutils - wc"""

    NAME = "coreutils_wc"
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS
    FEATURE_MODEL = "coreutils/wc.xml"

    SOURCE = _coreutils_source(NAME)
    WORKLOADS = {
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("coreutils") / RSBinary("wc"),
                ConfigParams(),
                "coreutils-workloads/jrc-en-full.xml",
                label="default"
            )
        ]
    }

    CONTAINER = _coreutils_container()

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        return _coreutils_binary_map("wc")[revision]

    def run_tests(self) -> None:
        _coreutils_run_tests(self)

    def compile(self) -> None:
        _coreutils_compile(self)
