"""
TODO: module docs
"""
import typing as tp
import os
import logging
from pathlib import Path
import shutil

from PyQt5.QtCore import (QProcess)

from plumbum import local
from plumbum.cmd import mkdir, ln

from varats.settings import CFG, save_config
from varats.tools.research_tools.research_tool import (ResearchTool, CodeBase,
                                                       SubProject)
from varats.vara_manager import (BuildType, run_process_with_output,
                                 set_vara_cmake_variables, ProcessManager)
from varats.utils.exceptions import ProcessTerminatedError

LOG = logging.getLogger(__name__)


class VaRACodeBase(CodeBase):

    def __init__(self, base_dir: Path) -> None:
        sub_projects = [
            SubProject("vara-llvm-project",
                       "https://github.com/llvm/llvm-project.git", "upstream",
                       "vara-llvm-project"),
            SubProject("VaRA", "git@github.com:se-passau/VaRA.git", "origin",
                       "vara-llvm-project/vara")
        ]
        if CFG["vara"]["with_phasar"].value:
            sub_projects.append(
                SubProject(
                    "phasar",
                    "https://github.com/secure-software-engineering/phasar.git",
                    "origin", "vara-llvm-project/phasar"))
        super().__init__(base_dir, sub_projects)

    def setup_vara_remotes(self) -> None:
        """
        Sets up VaRA specific upstream remotes for projects that where forked.
        """
        self.get_sub_project("vara-llvm-project").add_remote(
            self.base_dir, "origin",
            "git@github.com:se-passau/vara-llvm-project.git")

    def setup_build_link(self):
        """
        Setup build-config folder link for VaRAs default build setup scripts.
        """
        llvm_project_dir = self.base_dir / self.get_sub_project(
            "vara-llvm-project").path
        mkdir(llvm_project_dir / "build/")
        with local.cwd(llvm_project_dir / "build/"):
            ln("-s", llvm_project_dir / "vara/utils/vara/builds/", "build_cfg")

    def checkout_vara_version(self, version: int,
                              use_dev_branches: bool) -> None:
        """
        Checkout out a specific version of VaRA.

        Args:
            version: major version number, e.g., 100 or 110
            use_dev_branches: true, if one wants the current development version
        """
        dev_suffix = "-dev" if use_dev_branches else ""
        LOG.info(f"Checking out VaRA version {version}" + dev_suffix)

        self.get_sub_project("vara-llvm-project").checkout_branch(
            self.base_dir, f"vara-{version}" + dev_suffix)

        # TODO (sattlerf): make different checkout for older versions
        self.get_sub_project("VaRA").checkout_branch(self.base_dir,
                                                     f"vara" + dev_suffix)
        if use_dev_branches and CFG["vara"]["with_phasar"].value:
            self.get_sub_project("phasar").checkout_branch(
                self.base_dir, "development")


class VaRA(ResearchTool):

    def __init__(self, base_dir: Path) -> None:
        super().__init__([BuildType.DEV], VaRACodeBase(base_dir))

    @property
    def vara_code_base(self) -> VaRACodeBase:  # TODO: ask sebi about typing
        if isinstance(self.code_base, VaRACodeBase):
            return self.code_base
        raise TypeError

    def setup(self, source_folder: Path, **kwargs) -> None:
        LOG.info(f"Setting up VaRA at {source_folder}")
        CFG["vara"]["llvm_source_dir"] = str(source_folder)
        CFG["vara"]["llvm_install_dir"] = str(kwargs["install_prefix"])
        save_config()

        version = CFG["vara"]["version"].value
        use_dev_branches = CFG["vara"]["developer_version"].value

        self.code_base.clone(source_folder)
        self.vara_code_base.setup_vara_remotes()
        self.vara_code_base.checkout_vara_version(version, use_dev_branches)
        self.vara_code_base.setup_build_link()

    def update(self) -> None:
        pass

    def build(self, build_type: BuildType) -> None:
        full_path = self.code_base.base_dir / "vara-llvm-project" / "build/"
        if not self.is_build_type_supported(build_type):
            LOG.critical(
                f"BuildType {build_type.name} is not supported by VaRA")
            return

        full_path /= build_type.build_folder()

        # Setup configured build folder
        if not os.path.exists(full_path):
            try:
                os.makedirs(full_path.parent, exist_ok=True)
                build_script = "./build_cfg/build-{build_type}.sh".format(
                    build_type=str(build_type))

                with ProcessManager.create_process(
                        build_script, workdir=full_path.parent) as proc:
                    proc.setProcessChannelMode(QProcess.MergedChannels)
                    proc.readyReadStandardOutput.connect(
                        lambda: run_process_with_output(proc, print)
                    )  # TODO: post_out? update_term ?
            except ProcessTerminatedError as error:
                shutil.rmtree(full_path)
                raise error

        # Set install prefix in cmake
        with local.cwd(full_path):
            set_vara_cmake_variables(CFG["vara"]["llvm_install_dir"].value,
                                     print)

        # Compile llvm + VaRA
        with ProcessManager.create_process("ninja", ["install"],
                                           workdir=full_path) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda: run_process_with_output(proc, print))
