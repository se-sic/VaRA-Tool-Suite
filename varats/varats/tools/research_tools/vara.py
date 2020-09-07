"""Module for the research tool VaRA that describes the VaRA code base layout
and how to configure and setup VaRA."""
import logging
import os
import shutil
import typing as tp
from pathlib import Path

from benchbuild.utils.cmd import ln, mkdir
from plumbum import local
from PyQt5.QtCore import QProcess

from varats.plots.plot_utils import check_required_args
from varats.tools.research_tools.research_tool import (
    CodeBase,
    ResearchTool,
    SubProject,
)
from varats.tools.research_tools.vara_manager import (
    BuildType,
    ProcessManager,
    run_process_with_output,
    set_vara_cmake_variables,
)
from varats.utils.exceptions import ProcessTerminatedError
from varats.utils.logger_util import log_without_linesep
from varats.utils.settings import save_config, vara_cfg

LOG = logging.getLogger(__name__)


class VaRACodeBase(CodeBase):
    """Layout of the VaRA code base: setting up vara-llvm-project fork, VaRA,
    and optinaly phasar for static analysis."""

    def __init__(self, base_dir: Path) -> None:
        sub_projects = [
            SubProject(
                self, "vara-llvm-project",
                "https://github.com/llvm/llvm-project.git", "upstream",
                "vara-llvm-project"
            ),
            SubProject(
                self, "VaRA", "git@github.com:se-passau/VaRA.git", "origin",
                "vara-llvm-project/vara"
            ),
            SubProject(
                self,
                "phasar",
                "https://github.com/secure-software-engineering/phasar.git",
                "origin",
                "vara-llvm-project/phasar",
                auto_clone=False
            )
        ]
        super().__init__(base_dir, sub_projects)

    def setup_vara_remotes(self) -> None:
        """Sets up VaRA specific upstream remotes for projects that were
        forked."""
        self.get_sub_project("vara-llvm-project").add_remote(
            "origin", "git@github.com:se-passau/vara-llvm-project.git"
        )

    def setup_build_link(self) -> None:
        """Setup build-config folder link for VaRA's default build setup
        scripts."""
        llvm_project_dir = self.base_dir / self.get_sub_project(
            "vara-llvm-project"
        ).path
        mkdir(llvm_project_dir / "build/")
        with local.cwd(llvm_project_dir / "build/"):
            ln("-s", "../vara/utils/vara/builds/", "build_cfg")

    def checkout_vara_version(
        self, version: int, use_dev_branches: bool
    ) -> None:
        """
        Checkout out a specific version of VaRA.

        Args:
            version: major version number, e.g., 100 or 110
            use_dev_branches: true, if one wants the current development version
        """
        dev_suffix = "-dev" if use_dev_branches else ""
        print(f"Checking out VaRA version {str(version) + dev_suffix}")

        self.get_sub_project("vara-llvm-project"
                            ).checkout_branch(f"vara-{version}{dev_suffix}")

        # TODO (sattlerf): make different checkout for older versions
        self.get_sub_project("VaRA").checkout_branch(f"vara{dev_suffix}")

    def setup_submodules(self) -> None:
        """Set up the git submodules of all sub projects."""
        self.get_sub_project("vara-llvm-project").init_and_update_submodules()
        self.get_sub_project("phasar").init_and_update_submodules()

    def pull(self) -> None:
        """Pull and update all ``SubProject`` s."""
        self.map_sub_projects(lambda prj: prj.pull())
        self.setup_submodules()


class VaRA(ResearchTool[VaRACodeBase]):
    """
    Research tool implementation for VaRA.

    Find the main repo online on github: https://github.com/se-passau/VaRA
    """

    def __init__(self, base_dir: Path) -> None:
        super().__init__("VaRA", [BuildType.DEV], VaRACodeBase(base_dir))
        vara_cfg()["vara"]["llvm_source_dir"] = str(base_dir)
        save_config()

    @staticmethod
    def source_location() -> Path:
        """Returns the source location of the research tool."""
        return Path(vara_cfg()["vara"]["llvm_source_dir"].value)

    @staticmethod
    def has_source_location() -> bool:
        """Checks if a source location of the research tool is configured."""
        return vara_cfg()["vara"]["llvm_source_dir"].value is not None

    @staticmethod
    def install_location() -> Path:
        """Returns the install location of the research tool."""
        return Path(vara_cfg()["vara"]["llvm_install_dir"].value)

    @staticmethod
    def has_install_location() -> bool:
        """Checks if a install location of the research tool is configured."""
        return vara_cfg()["vara"]["llvm_install_dir"].value is not None

    @check_required_args(["install_prefix", "version"])
    def setup(self, source_folder: tp.Optional[Path], **kwargs: tp.Any) -> None:
        """
        Setup the research tool VaRA with it's code base. This method sets up
        all relevant config variables, downloads repositories via the
        ``CodeBase``, checkouts the correct branches and prepares the research
        tool to be built.

        Args:
            source_folder: location to store the code base in
            **kwargs:
                      * version
                      * install_prefix
        """
        cfg = vara_cfg()
        if source_folder:
            cfg["vara"]["llvm_source_dir"] = str(source_folder)
        cfg["vara"]["llvm_install_dir"] = str(kwargs["install_prefix"])
        version = kwargs.get("version")
        if version:
            version = int(tp.cast(int, version))
            cfg["vara"]["version"] = version
        else:
            version = cfg["vara"]["version"].value
        save_config()

        print(f"Setting up VaRA in {self.source_location()}")

        use_dev_branches = cfg["vara"]["developer_version"].value

        self.code_base.clone(self.source_location())
        self.code_base.setup_vara_remotes()
        self.code_base.checkout_vara_version(version, use_dev_branches)
        self.code_base.setup_submodules()
        self.code_base.setup_build_link()

    def upgrade(self) -> None:
        """Upgrade the research tool to a newer version."""
        version = 100

        # TODO (se-passau/VaRA#640): version upgrade
        if str(vara_cfg()["vara"]["version"]) != str(version):
            raise NotImplementedError

        self.code_base.pull()

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
                f"BuildType {build_type.name} is not supported by VaRA"
            )
            return

        full_path /= build_type.build_folder()

        # Setup configured build folder
        print(" - Setting up build folder.")
        if not os.path.exists(full_path):
            try:
                os.makedirs(full_path.parent, exist_ok=True)
                build_script = "./build_cfg/build-{build_type}.sh".format(
                    build_type=str(build_type)
                )

                with ProcessManager.create_process(
                    build_script, workdir=full_path.parent
                ) as proc:
                    proc.setProcessChannelMode(QProcess.MergedChannels)
                    proc.readyReadStandardOutput.connect(
                        lambda: run_process_with_output(
                            proc, log_without_linesep(print)
                        )
                    )
            except ProcessTerminatedError as error:
                shutil.rmtree(full_path)
                raise error
        print(" - Finished setup of build folder.")

        # Set install prefix in cmake
        with local.cwd(full_path):
            vara_cfg()["vara"]["llvm_install_dir"] = str(install_location)
            set_vara_cmake_variables(
                str(install_location), log_without_linesep(print)
            )
        print(" - Finished extra cmake config.")

        print(" - Now building...")
        # Compile llvm + VaRA
        with ProcessManager.create_process(
            "ninja", ["install"], workdir=full_path
        ) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda:
                run_process_with_output(proc, log_without_linesep(print))
            )

    def verify_install(self, install_location: Path) -> bool:
        # pylint: disable=no-self-use
        """
        Verify if VaRA was correctly installed.

        Returns:
            True, if the tool was correctly installed
        """
        status_ok = True
        status_ok &= (install_location / "bin/clang++").exists()
        status_ok &= (install_location / "bin/opt").exists()
        status_ok &= (install_location / "bin/phasar-llvm").exists()

        return status_ok
