"""Module for the research tool phasar that describes the phasar code base
layout and implements automatic configuration and setup."""
import os
import shutil
import typing as tp
from pathlib import Path

from plumbum import local
from PyQt5.QtCore import QProcess

from varats.tools.research_tools.cmake_util import set_cmake_var
from varats.tools.research_tools.research_tool import (
    CodeBase,
    ResearchTool,
    SubProject,
    Dependencies,
    Distro,
)
from varats.tools.research_tools.vara_manager import (
    BuildType,
    ProcessManager,
    run_process_with_output,
)
from varats.utils.exceptions import ProcessTerminatedError
from varats.utils.logger_util import log_without_linesep
from varats.utils.settings import save_config, vara_cfg

if tp.TYPE_CHECKING:
    from varats.containers import containers  # pylint: disable=W0611


class PhasarCodeBase(CodeBase):
    """Layout of the phasar code base."""

    def __init__(self, base_dir: Path) -> None:
        sub_projects = [
            SubProject(
                self, "phasar",
                "https://github.com/secure-software-engineering/phasar.git",
                "origin", "phasar"
            )
        ]
        super().__init__(base_dir, sub_projects)

    def checkout_phasar_version(self, use_dev_branch: bool) -> None:
        """
        Checkout out a specific version of phasar.

        Args:
            use_dev_branche: true, if one wants the current development version
        """
        if use_dev_branch:
            branch_name = "development"
        else:
            branch_name = "master"

        print(f"Checking out phasar version {branch_name}")

        self.get_sub_project("phasar").checkout_branch(branch_name)

    def setup_submodules(self) -> None:
        """Set up the git submodules of all sub projects."""
        self.get_sub_project("phasar").init_and_update_submodules()

    def pull(self) -> None:
        """Pull and update all ``SubProject`` s."""
        self.map_sub_projects(lambda prj: prj.pull())
        self.setup_submodules()


class Phasar(ResearchTool[PhasarCodeBase]):
    """
    Research tool implementation for phasar.

    Find the main repo online on github:
    https://github.com/secure-software-engineering/phasar.git
    """

    __DEPENDENCIES = Dependencies({
        Distro.DEBIAN: [
            "libboost-all-dev", "zlib1g-dev", "sqlite3", "libsqlite3-dev",
            "bear", "python3", "doxygen", "graphviz", "python3-pip", "libxml2",
            "libxml2-dev", "libncurses5-dev", "libncursesw5-dev", "swig",
            "build-essential", "g++", "cmake", "libz3-dev", "libedit-dev",
            "python3-sphinx", "libomp-dev", "libcurl4-openssl-dev",
            "ninja-build"
        ],
        Distro.ARCH: [
            "boost-libs", "boost", "which", "zlib", "sqlite3", "ncurses",
            "make", "python3", "doxygen", "libxml2", "swig", "gcc", "cmake",
            "z3", "libedit", "graphviz", "python-sphinx", "openmp", "curl",
            "python-pip"
        ]
    })

    def __init__(self, base_dir: Path) -> None:
        super().__init__("phasar", [BuildType.DEV], PhasarCodeBase(base_dir))
        vara_cfg()["phasar"]["source_dir"] = str(base_dir)
        save_config()

    @classmethod
    def get_dependencies(cls) -> Dependencies:
        return cls.__DEPENDENCIES

    @staticmethod
    def source_location() -> Path:
        """Returns the source location of the research tool."""
        return Path(vara_cfg()["phasar"]["source_dir"].value)

    @staticmethod
    def has_source_location() -> bool:
        """Checks if a source location of the research tool is configured."""
        return vara_cfg()["phasar"]["source_dir"].value is not None

    @staticmethod
    def install_location() -> Path:
        """Returns the install location of the research tool."""
        return Path(vara_cfg()["phasar"]["install_dir"].value)

    @staticmethod
    def has_install_location() -> bool:
        """Checks if a install location of the research tool is configured."""
        return vara_cfg()["phasar"]["install_dir"].value is not None

    def setup(
        self, source_folder: tp.Optional[Path], install_prefix: Path,
        version: tp.Optional[int]
    ) -> None:
        """
        Setup the research tool phasar with it's code base. This method sets up
        all relevant config variables, downloads repositories via the
        ``CodeBase``, checkouts the correct branches and prepares the research
        tool to be built.

        Args:
            source_folder: location to store the code base in
            install_prefix: Installation prefix path
            version: Version to setup
        """
        cfg = vara_cfg()
        if source_folder:
            cfg["phasar"]["source_dir"] = str(source_folder)
        cfg["phasar"]["install_dir"] = str(install_prefix)
        save_config()

        print(f"Setting up phasar in {self.source_location()}")

        use_dev_branch = cfg["phasar"]["developer_version"].value

        self.code_base.clone(self.source_location())
        self.code_base.checkout_phasar_version(use_dev_branch)
        self.code_base.setup_submodules()

    def upgrade(self) -> None:
        """Upgrade the research tool to a newer version."""
        self.code_base.pull()

    def build(
        self, build_type: BuildType, install_location: Path,
        build_folder_suffix: tp.Optional[str]
    ) -> None:
        """
        Build/Compile phasar in the specified ``build_type``. This method leaves
        phasar in a finished state, i.e., being ready to be installed.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release
        """
        build_path = self.code_base.base_dir / self.code_base.get_sub_project(
            "phasar"
        ).path / "build"

        build_path /= build_type.build_folder(build_folder_suffix)

        # Setup configured build folder
        print(" - Setting up build folder.")
        if not os.path.exists(build_path):
            try:
                os.makedirs(build_path, exist_ok=True)
                with ProcessManager.create_process(
                    "cmake", ["-G", "Ninja", "../.."], workdir=build_path
                ) as proc:
                    proc.setProcessChannelMode(QProcess.MergedChannels)
                    proc.readyReadStandardOutput.connect(
                        lambda: run_process_with_output(
                            proc, log_without_linesep(print)
                        )
                    )
            except ProcessTerminatedError as error:
                shutil.rmtree(build_path)
                raise error
        print(" - Finished setup of build folder.")

        with local.cwd(build_path):
            vara_cfg()["phasar"]["install_dir"] = str(install_location)
            set_cmake_var(
                "CMAKE_INSTALL_PREFIX", str(install_location),
                log_without_linesep(print)
            )
        print(" - Finished extra cmake config.")

        print(" - Now building...")
        with ProcessManager.create_process(
            "ninja", ["install"], workdir=build_path
        ) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda:
                run_process_with_output(proc, log_without_linesep(print))
            )

    def verify_install(self, install_location: Path) -> bool:
        # pylint: disable=no-self-use
        """
        Verify if phasar was correctly installed.

        Returns:
            True, if the tool was correctly installed
        """
        status_ok = True
        status_ok &= (install_location / "bin/myphasartool").exists()
        status_ok &= (install_location / "bin/phasar-llvm").exists()

        return status_ok

    def verify_build(
        self, build_type: BuildType, build_folder_suffix: tp.Optional[str]
    ) -> bool:
        return True

    def container_add_build_layer(
        self, image_context: 'containers.BaseImageCreationContext'
    ) -> None:
        """
        Add layers for building this research tool to the given container.

        Args:
            image_context: the base image creation context
        """
        raise NotImplementedError

    def container_install_tool(
        self, image_context: 'containers.BaseImageCreationContext'
    ) -> None:
        """
        Add layers for installing this research tool to the given container.

        Args:
            image_context: the base image creation context
        """
        if not self.verify_install(self.install_location()):
            raise AssertionError(
                "Phasar is not correctly installed on your system."
            )

        container_phasar_dir = image_context.varats_root / "tools/phasar"
        image_context.layers.copy_([str(self.install_location())],
                                   str(container_phasar_dir))
        image_context.append_to_env("PATH", [str(container_phasar_dir / 'bin')])
