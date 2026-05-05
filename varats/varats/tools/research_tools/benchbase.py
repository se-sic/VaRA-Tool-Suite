"""Module for the research tool benchbase that describes the benchbase code base
layout and implements automatic configuration and setup."""
import shutil
import typing as tp
from pathlib import Path

from plumbum import local
from PyQt5.QtCore import QProcess

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


class BenchbaseCodeBase(CodeBase):
    """Layout of the benchbase code base."""

    def __init__(self, base_dir: Path) -> None:
        sub_projects = [
            SubProject(
                base_dir, "benchbase",
                "https://github.com/cmu-db/benchbase.git", "origin", "benchbase"
            )
        ]

        super().__init__(base_dir, sub_projects)


class Benchbase(ResearchTool[BenchbaseCodeBase]):
    """Research tool for benchbase."""

    __DEPENDENCIES = Dependencies({Distro.DEBIAN: [], Distro.ARCH: []})

    __SUPPORTED_PROFILES = ["postgres", "mysql", "mariadb"]

    def __init__(self, base_dir: Path) -> None:
        super().__init__(
            "benchbase", [BuildType.DEV], BenchbaseCodeBase(base_dir)
        )

    @classmethod
    def get_dependencies(cls) -> Dependencies:
        return cls.__DEPENDENCIES

    @staticmethod
    def source_location() -> Path:
        return Path(vara_cfg()["benchbase"]["source_dir"].value)

    @staticmethod
    def has_source_location() -> bool:
        return vara_cfg()["benchbase"]["source_dir"].value is not None

    @staticmethod
    def install_location() -> Path:
        # Check if container environment variable is set
        if (container_install_dir := local.env.get("BENCHBASE_INSTALL_DIR")):
            return Path(container_install_dir)
        return Path(vara_cfg()["benchbase"]["install_dir"].value)

    @staticmethod
    def has_install_location() -> bool:
        return vara_cfg()["benchbase"]["install_dir"].value is not None

    @staticmethod
    def get_java_dir() -> Path:
        return Path(vara_cfg()["benchbase"]["java_dir"].value)

    @staticmethod
    def get_benchbase_target(profile: str) -> Path:
        install_path = Benchbase.install_location() / f"benchbase-{profile}.tgz"
        if not install_path.exists():
            print(f"Benchbase target {install_path} does not exist.")
            return Path()
        return install_path

    def setup(
        self, source_folder: tp.Optional[Path], install_prefix: Path,
        version: tp.Optional[int]
    ) -> None:
        cfg = vara_cfg()
        if source_folder:
            cfg["benchbase"]["source_dir"] = str(source_folder)
        cfg["benchbase"]["install_dir"] = str(install_prefix)
        save_config()

        print(f"Setting up benchbase in {self.source_location()}")

        self.code_base.clone(self.source_location())

    def is_up_to_date(self) -> bool:
        return True

    def upgrade(self) -> None:
        self.code_base.get_sub_project("benchbase").pull()

    def build(
        self, build_type: BuildType, install_location: Path,
        build_folder_suffix: tp.Optional[str]
    ) -> None:
        build_path = self.code_base.base_dir / self.code_base.get_sub_project(
            "benchbase"
        ).path

        print(" - Setting up build directory")

        if not build_path.exists():
            build_path.mkdir(parents=True, exist_ok=True)

        java_23_dir = vara_cfg()["benchbase"]["java_dir"].value
        if java_23_dir is None:
            raise AssertionError(
                "Java 23 directory is not set in config, cannot build benchbase."
            )

        with local.env(
            JAVA_HOME=java_23_dir,
            PATH=f"{java_23_dir}/bin:" + local.env["PATH"]
        ):
            try:
                for profile in self.__SUPPORTED_PROFILES:
                    print(f" - Building benchbase with profile {profile}")
                    with ProcessManager.create_process(
                        "./mvnw", ["clean", "package", "-P", profile],
                        workdir=build_path
                    ) as proc:
                        proc.setProcessChannelMode(QProcess.MergedChannels)
                        proc.readyReadStandardOutput.connect(
                            lambda: run_process_with_output(
                                proc, log_without_linesep(print)
                            )
                        )
                    print(
                        f" - Finished building benchbase with profile {profile}"
                    )

                    print(" - Moving tgz to install dir.")
                    tgz_file = build_path / "target" / f"benchbase-{profile}.tgz"
                    if not tgz_file.exists():
                        raise AssertionError(
                            f"Expected tgz file {tgz_file} does not exist after build."
                        )

                    # Move all files to install location
                    shutil.move(
                        str(tgz_file), str(install_location / tgz_file.name)
                    )
            except ProcessTerminatedError as error:
                print(
                    " - Error during Maven build, cleaning up build directory"
                )
                shutil.rmtree(build_path)
                raise error
        print(" - Finished building benchbase")

    def get_install_binaries(self) -> tp.List[str]:
        return [
            f"benchbase-{profile}.tgz" for profile in self.__SUPPORTED_PROFILES
        ]

    def verify_build(
        self, build_type: BuildType, build_folder_suffix: tp.Optional[str]
    ) -> bool:
        return True

    #################################
    # ContainerInstallable Protocol #
    #################################

    def container_install_dependencies(
        self, stage_builder: 'containers.StageBuilder'
    ) -> None:
        """
        Add layers for installing this research tool's dependencies to the given
        container.

        Args:
            stage_builder: the builder object for the current container stage
        """

        if self.get_dependencies().has_dependencies_for_distro(
            stage_builder.base.distro
        ):
            # Distribution-specific dependencies
            ...

    def container_install_tool(
        self, stage_builder: 'containers.StageBuilder'
    ) -> None:
        """
        Add layers for installing this research tool to the given container.

        Args:
            stage_builder: the builder object for the current container stage
        """
        img_name = stage_builder.base.name
        benchbase_install_dir = str(self.install_location()) + "_" + img_name
        if not self.install_exists(Path(benchbase_install_dir)):
            raise AssertionError(
                f"Could not find VaRA build for base container {img_name}.\n"
                f"Run 'vara-buildsetup build vara --container={img_name}' "
                f"to compile VaRA for this base image."
            )

        container_vara_dir = stage_builder.varats_root / (
            "tools/benchbase_" + img_name
        )
        stage_builder.layers.copy_([benchbase_install_dir],
                                   str(container_vara_dir))

        # In addition, install stable Java 23 via Adoptium
        jdk_download_url = "https://github.com/adoptium/temurin23-binaries/releases/download/jdk-23.0.2%2B7/OpenJDK23U-jdk_x64_linux_hotspot_23.0.2_7.tar.gz"
        base_dir = self.code_base.base_dir
        jdk_target = base_dir / "jdk-23.tar.gz"
        if jdk_target.exists():
            jdk_target.unlink()
        local["wget"][jdk_download_url, "-O", str(jdk_target)]()

        # Extract the JDK to the base directory and then copy it to the container
        jdk_extract_path = base_dir / "jdk-23.0.2+7"
        if jdk_extract_path.exists():
            shutil.rmtree(jdk_extract_path)

        local["tar"]["-xzf", str(jdk_target)]()

        container_jdk_dir = stage_builder.varats_root / "jdk-23"
        stage_builder.layers.copy_([str(jdk_extract_path)], container_jdk_dir)

    def container_tool_env(
        self, stage_builder: 'containers.StageBuilder'
    ) -> tp.Dict[str, tp.List[str]]:
        """
        Tool-specific container configuration in the form of environment
        variables.

        Args:
            stage_builder: the builder object for the current container stage
        Returns:
            a dictionary of environment variables and their values
        """

        # Paths to adapt for container environment:
        # JAVA_HOME - To point to correct JDK installation in the container
        # PATH - To include the bin directory of the JDK in the container
        # BENCHBASE_INSTALL_DIR - To point to the correct location of the benchbase tgz in the container

        return {
            "JAVA_HOME": [str(stage_builder.varats_root / "jdk-23")],
            "PATH": [str(stage_builder.varats_root / "jdk-23" / "bin")],
            "BENCHBASE_INSTALL_DIR": [
                "/varats_root/tools/benchbase_" + stage_builder.base.name
            ]
        }
