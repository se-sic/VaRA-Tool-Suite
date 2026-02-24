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

    __DEPENDENCIES = Dependencies({Distro.DEBIAN: ["ninja-build"]})

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

        print(f"{java_23_dir=}")

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
        return []

    def verify_build(
        self, build_type: BuildType, build_folder_suffix: tp.Optional[str]
    ) -> bool:
        return True
