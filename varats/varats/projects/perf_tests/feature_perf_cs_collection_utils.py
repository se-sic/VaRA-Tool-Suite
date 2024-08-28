import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import make, cmake, mkdir
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.project.project_util import verify_binaries
from varats.project.varats_project import VProject
from varats.utils.git_commands import init_all_submodules, update_all_submodules
from varats.utils.git_util import RepositoryHandle
from varats.utils.settings import bb_cfg


def do_feature_perf_cs_collection_compile(
    project: VProject, cmake_flag: tp.Optional[str] = None
) -> None:
    """Common compile function for FeaturePerfCSCollection projects."""
    feature_perf_repo = RepositoryHandle(Path(project.source_of_primary))

    cc_compiler = bb.compiler.cc(project)
    cxx_compiler = bb.compiler.cxx(project)

    mkdir("-p", feature_perf_repo.worktree_path / "build")

    init_all_submodules(feature_perf_repo)
    update_all_submodules(feature_perf_repo)

    with local.cwd(feature_perf_repo.worktree_path / "build"):
        with local.env(CC=str(cc_compiler), CXX=str(cxx_compiler)):
            bb.watch(cmake)("..", "-G", "Unix Makefiles", f"-D{cmake_flag}=ON")

        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))

    with local.cwd(feature_perf_repo.worktree_path):
        verify_binaries(project)


def do_feature_perf_cs_collection_recompile(project: VProject) -> None:
    feature_perf_source = local.path(project.source_of(project.primary_source))

    with local.cwd(feature_perf_source / "build"):
        bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
