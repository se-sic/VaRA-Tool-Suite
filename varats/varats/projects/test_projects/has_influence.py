"""Example project for feature analyses."""
import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.source import HTTPMultiple
from plumbum import local
from benchbuild.utils.cmd import cmake
from benchbuild.utils.settings import get_number_of_jobs

from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    verify_binaries,
    BinaryType,
    get_local_project_git_path,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.sources import FeatureSource
from varats.project.varats_project import VProject
from varats.ts_utils.project_sources import VaraTestRepoSource
from varats.utils.git_util import ShortCommitHash, RevisionBinaryMap
from varats.utils.settings import bb_cfg


class HasInfluence(VProject):
    """Example project for feature analyses."""

    NAME = 'HasInfluence'
    GROUP = 'test_projects'
    DOMAIN = ProjectDomains.TEST

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="HasInfluence",
            remote="https://github.com/TheOneAndOnlyTobi/HasInfluence.git",
            local="HasInfluence",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        HTTPMultiple(
            local="test-files",
            remote={
                "1.0":
                    "https://raw.githubusercontent.com/itsfoss/text-files/master/"
            },
            files=["agatha.txt", "sherlock.txt", "sample_log_file.txt", "agatha_complete.txt"]
        )
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("HasInfluence") / RSBinary("HasInfluence"),
                "--f1",
                "--f2",
                "--f3",
                "test-files/agatha.txt",
                label="agatha"
            ),
        ]
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(HasInfluence.NAME)
        ).specify_binary("HasInfluence", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the example project."""
        source = local.path(self.source_of_primary)

        cc_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(source):
            with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("./")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

            verify_binaries(self)