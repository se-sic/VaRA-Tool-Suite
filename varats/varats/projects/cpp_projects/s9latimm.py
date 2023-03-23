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
    # $ pip install -e ../vara-tool-suite/varats-core
    # $ pip install -e ../vara-tool-suite/varats

    # $ vara-pc create s9latimm
    # $ vara-pc select
    # $ vara-cs gen --project s9latimm select_latest

    # $ LOG_LEVEL=debug vara-buildsetup build vara --container=DEBIAN_10
    # $ LOG_LEVEL=debug vara-container build --force-rebuild --export

    # $ git -C ../vara-tool-suite fetch --recurse-submodules
    # $ git -C ../vara-tool-suite pull --recurse-submodules
    # $ LOG_LEVEL=debug vara-container build --update-tool-suite --export

    # $ vara-run -vv --container --slurm --experiment RunFeatureVaRAXRayPerf s9latimm
    # $ nano benchbuild/RunFeatureVaRAXRayPerf-slurm.sh

    # $ sbatch --constraint=maxl --mem=128GB --time=30 benchbuild/RunFeatureVaRAXRayPerf-slurm.sh
    # $ watch -n 1 -d squeue --me
    # $ tail -f $(ls -1dptA benchbuild/slurm_logs/* | egrep -v /$ | head -1)

    # $ vara-cs status RunFeatureVaRAXRayPerf
    # $ unzip -l results/s9latimm/*.zip
    # $ vara-cs cleanup --experiment RunFeatureVaRAXRayPerf all
    # $ vara-cs cleanup --experiment RunFeatureVaRAXRayPerf --case-studies s9latimm_0 all
    # $ rm -rf benchbuild/slurm_logs/*

    # $ alias bbuildah='buildah --root /local/storage/s9latimm/benchbuild/containers/lib --runroot /local/storage/s9latimm/benchbuild/containers/run --storage-driver=vfs'
    # $ bbuildah images
    # $ bbuildah rmi --force --all

    # REPOSITORY                 TAG                            SIZE
    # localhost/debian_10        stage_30_config_vara           7.56 GB
    # localhost/debian_10        stage_20_tool_vara             7.56 GB
    # localhost/debian_10        stage_10_varats_vara           4.48 GB
    # localhost/debian_10        stage_00_base_vara             3.15 GB
    # localhost/debian_10        stage_31_config_dev_vara_dev   4.48 GB
    # localhost/debian_10        stage_10_varats_vara_dev       4.48 GB
    # localhost/debian_10        stage_00_base_vara_dev         3.15 GB
    # docker.io/library/debian   10                             119 MB

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
