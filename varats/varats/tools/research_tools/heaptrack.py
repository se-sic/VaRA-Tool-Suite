"""Module for the KDE tool heaptrack that describes the heaptrack code base
layout and implements automatic configuration and setup."""
import shutil
import typing as tp
from pathlib import Path

from plumbum import local
from PyQt5.QtCore import QProcess

from varats.tools.research_tools.cmake_util import set_cmake_var
from varats.tools.research_tools.research_tool import (
    CodeBase,
    SubProject,
    ResearchTool,
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
from varats.utils.settings import vara_cfg, save_config


class HeapTrackCodeBase(CodeBase):
    """Layout of the heaptrack code base."""

    def __init__(self, base_dir: Path) -> None:
        sub_projects = [
            SubProject(
                base_dir, "heaptrack",
                "https://invent.kde.org/sdk/heaptrack.git", "origin",
                "heaptrack"
            )
        ]

        super().__init__(base_dir, sub_projects)


class HeapTrack(ResearchTool[HeapTrackCodeBase]):
    """Heaptrack is a tool for tracking and analyzing heap memory usage in
    applications."""
    __DEPENDENCIES = Dependencies({
        Distro.DEBIAN: [
            "zlib1g-dev", "zstd", "elfutils", "libc6-dev",
            " libpthread-stubs0-dev", "libunwind-dev", "cmake",
            "libboost-iostreams-dev", "libboost-program-options-dev", "cmake",
            "ninja-build"
        ],
    })

    def __init__(self, base_dir: Path) -> None:
        super().__init__(
            "heaptrack", [BuildType.DEV], HeapTrackCodeBase(base_dir)
        )
        vara_cfg()["heaptrack"]["source_dir"] = str(base_dir)
        save_config()

    @classmethod
    def get_dependencies(cls) -> Dependencies:
        return cls.__DEPENDENCIES

    @staticmethod
    def source_location() -> Path:
        """Get the source location of heaptrack."""
        return Path(vara_cfg()["heaptrack"]["source_dir"].value)

    @staticmethod
    def has_source_location() -> bool:
        """Check if a source location for heaptrack is configured."""
        return vara_cfg()["heaptrack"]["source_dir"].value is not None

    @staticmethod
    def install_location() -> Path:
        """Return the install location of heaptrack."""
        return Path(vara_cfg()["heaptrack"]["install_dir"].value)

    @staticmethod
    def has_install_location() -> bool:
        """Check if an install location for heaptrack is configured."""
        return vara_cfg()["heaptrack"]["install_dir"].value is not None

    def is_up_to_date(self) -> bool:
        """Check if heaptrack is up to date."""
        return True

    def setup(
        self, source_folder: tp.Optional[Path], install_prefix: Path,
        version: tp.Optional[int]
    ) -> None:
        """
        Setup the HeapTrack with it's code base. This method sets up all
        relevant config variables, downloads repositories via the ``CodeBase``,
        checkouts the correct branches and prepares the research tool to be
        built.

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

        print(f"Setting up heaptrack in {self.source_location()}")

        self.code_base.clone(self.source_location())

        # Checkout the correct version if specified ?

    def upgrade(self) -> None:
        """Upgrade heaptrack to the latest version."""
        self.code_base.get_sub_project("heaptrack").pull()

    def build(
        self, build_type: BuildType, install_location: Path,
        build_folder_suffix: tp.Optional[str]
    ) -> None:
        """Build and installs heaptrack in the specified build type."""

        build_path = self.code_base.base_dir / self.code_base.get_sub_project(
            "heaptrack"
        ).path / "build"
        build_path /= build_type.build_folder(build_folder_suffix)

        print(" - Setting up build directory")

        if not build_path.exists():
            build_path.mkdir(parents=True, exist_ok=True)

            try:
                with ProcessManager.create_process(
                    "cmake",
                    ["-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release", "../.."],
                    workdir=build_path
                ) as proc:
                    proc.setProcessChannelMode(QProcess.MergedChannels)
                    proc.readyReadStandardOutput.connect(
                        lambda: run_process_with_output(
                            proc, log_without_linesep(print)
                        )
                    )
            except ProcessTerminatedError as error:
                print(" - Error during CMake")
                shutil.rmtree(build_path)
                raise error
        print(" - Finished setting up build directory")

        with local.cwd(build_path):
            vara_cfg()["heaptrack"]["install_dir"] = str(install_location)
            set_cmake_var(
                "CMAKE_INSTALL_PREFIX", str(install_location),
                log_without_linesep(print)
            )
        print(" - Finished extra cmake config.")

        print(" - Building heaptrack")
        with ProcessManager.create_process(
            "ninja", ["install"], workdir=build_path
        ) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda:
                run_process_with_output(proc, log_without_linesep(print))
            )

    def get_install_binaries(self) -> tp.List[str]:
        return ["bin/heaptrack", "bin/heaptrack_print"]

    def verify_build(
        self, build_type: BuildType, build_folder_suffix: tp.Optional[str]
    ) -> bool:
        return True
