"""
Module for the research tool VaRA that describes the VaRA code base layout and
how to configure and setup VaRA.
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
from varats.utils.cli_util import log_without_linsep

LOG = logging.getLogger(__name__)


class VaRACodeBase(CodeBase):
    """
    Layout of the VaRA code base: setting up vara-llvm-project fork, VaRA, and
    optinaly phasar, for static analysis.
    """

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

    def setup_build_link(self) -> None:
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


class VaRA(ResearchTool[VaRACodeBase]):
    """
    Research tool implementation for VaRA.
    Find the main repo online on github: https://github.com/se-passau/VaRA
    """

    def __init__(self, base_dir: Path) -> None:
        super().__init__("VaRA", [BuildType.DEV], VaRACodeBase(base_dir))

    def setup(self, source_folder: Path, **kwargs: tp.Any) -> None:
        """
        Setup the research tool VaRA with it's code base. This method sets up
        all relevant config variables, downloads repositories via the
        ``CodeBase``, checkouts the correct branches and prepares the research
        tool to be build.

        Args:
            source_folder: location to store the code base in
            **kwargs:
                      * version
                      * install_prefix
        """
        CFG["vara"]["llvm_source_dir"] = str(source_folder)
        CFG["vara"]["llvm_install_dir"] = str(kwargs["install_prefix"])
        version = kwargs["version"]
        if version:
            version = int(tp.cast(int, version))
            CFG["vara"]["version"] = version
        else:
            version = CFG["vara"]["version"].value

        LOG.info(f"Setting up VaRA at {source_folder}")
        save_config()

        use_dev_branches = CFG["vara"]["developer_version"].value

        self.code_base.clone(source_folder)
        self.code_base.setup_vara_remotes()
        self.code_base.checkout_vara_version(version, use_dev_branches)
        self.code_base.setup_build_link()

    def upgrade(self) -> None:
        """
        Upgrade the research tool to a newer version.
        """
        raise NotImplementedError

    def build(self, build_type: BuildType, install_location: Path) -> None:
        """
        Build/Compile VaRA in the specified ``build_type``. This method leaves
        VaRA in a finished state, i.e., being ready to be installed.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release
        """
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
                        lambda: run_process_with_output(
                            proc, log_without_linsep(LOG.info)))
            except ProcessTerminatedError as error:
                shutil.rmtree(full_path)
                raise error

        # Set install prefix in cmake
        with local.cwd(full_path):
            CFG["vara"]["llvm_install_dir"] = str(install_location)
            set_vara_cmake_variables(str(install_location), LOG.info)

        # Compile llvm + VaRA
        with ProcessManager.create_process("ninja", ["install"],
                                           workdir=full_path) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda: run_process_with_output(proc,
                                                log_without_linsep(LOG.info)))
