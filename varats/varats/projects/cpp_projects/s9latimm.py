import typing as tp

import benchbuild as bb
from benchbuild.command import Command, SourceRoot, WorkloadSet
from benchbuild.utils.cmd import cmake, mkdir, git
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import RSBinary, WorkloadCategory
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import (
    RevisionBinaryMap,
    ShortCommitHash,
)
from varats.utils.settings import bb_cfg


class S9LaTimm(VProject):
    # benchbuild/.benchbuild.yml
    #   plugins:
    #       projects:
    #           - varats.projects.cpp_projects.s9latimm

    # $ source .venv/bin/activate
    # $ cd vara-root

    # $ vara-pc create s9latimm
    # $ vara-pc select
    # $ vara-cs gen --project s9latimm select_latest

    # $ git -C ../vara-tool-suite pull --recurse-submodules
    # $ LOG_LEVEL=debug vara-container build --update-tool-suite --export

    # $ vara-run -vv --container --slurm --experiment RunFeatureXRayPerf s9latimm
    # $ nano benchbuild/RunFeatureXRayPerf-slurm.sh

    # $ sbatch --constraint=maxl --mem=128GB --time=30 benchbuild/RunFeatureXRayPerf-slurm.sh
    # $ sbatch --constraint=eku --cpus-per-task 4 --mem=8GB --time=30 benchbuild/RunFeatureXRayPerf-slurm.sh
    # $ watch -n 1 -d squeue --me
    # $ tail -f $(ls -1dptA benchbuild/slurm_logs/* | egrep -v /$ | head -1)

    # $ vara-cs status RunFeatureXRayPerf
    # $ unzip -l  results/s9latimm/*.zip
    # $ vara-cs cleanup --experiment RunFeatureXRayPerf --case-studies s9latimm_0 all
    # $ rm -rf benchbuild/slurm_logs/*

    NAME = "s9latimm"
    GROUP = "cpp_projects"
    DOMAIN = ProjectDomains.WEB_TOOLS

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="s9latimm",
            remote="https://github.com/s9latimm/configurable-system.git",
            local="s9latimm",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10)

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            Command(
                SourceRoot("s9latimm") / RSBinary("main"),
                "foo",
                "bar",
                "buz",
                label="s9latimm",
            )
        ],
    }

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_git_path(S9LaTimm.NAME)
        )
        binary_map.specify_binary("build/main", BinaryType.EXECUTABLE)
        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        source = local.path(self.source_of_primary)

        with local.cwd(source):
            # always get newest version
            git("fetch")
            git("checkout", "origin/HEAD")

        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", source / "build")

        with local.cwd(source / "build"):
            with local.env(CXX=str(cxx_compiler)):
                bb.watch(cmake)("..")
                bb.watch(cmake
                        )("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(source):
            verify_binaries(self)
