"""Module for the tool SZZUnleashed."""

import logging
import re
import typing as tp
from pathlib import Path

import benchbuild as bb
from benchbuild.utils.cmd import gradle, cp
from plumbum import local

from varats.tools.research_tools.research_tool import (
    CodeBase,
    ResearchTool,
    SubProject,
)
from varats.tools.research_tools.vara_manager import BuildType
from varats.utils.settings import vara_cfg, save_config

LOG = logging.getLogger(__name__)


class SZZUnleashedCodeBase(CodeBase):
    """Layout of the SZZUnleashed code base."""

    def __init__(self, base_dir: Path):
        super().__init__(
            base_dir, [
                SubProject(
                    self, "SZZUnleashed",
                    "https://github.com/boehmseb/SZZUnleashed.git", "origin",
                    "szzunleashed"
                )
            ]
        )


class SZZUnleashed(ResearchTool[SZZUnleashedCodeBase]):
    """
    Research tool implementation for SZZUnleashed.

    Find the main repo on github: https://github.com/wogscpar/SZZUnleashed
    """

    def __init__(self, base_dir: Path) -> None:
        super().__init__(
            "SZZUnleashed", [BuildType.DEV], SZZUnleashedCodeBase(base_dir)
        )
        vara_cfg()["szzunleashed"]["source_dir"] = str(base_dir)
        save_config()

    @staticmethod
    def source_location() -> Path:
        """Returns the source location of the research tool."""
        return Path(vara_cfg()["szzunleashed"]["source_dir"].value)

    @staticmethod
    def has_source_location() -> bool:
        """Checks if a source location of the research tool is configured."""
        return vara_cfg()["szzunleashed"]["source_dir"].value is not None

    @staticmethod
    def install_location() -> Path:
        """Returns the install location of the research tool."""
        return Path(vara_cfg()["szzunleashed"]["install_dir"].value)

    @staticmethod
    def has_install_location() -> bool:
        """Checks if a install location of the research tool is configured."""
        return vara_cfg()["szzunleashed"]["install_dir"].value is not None

    def setup(self, source_folder: tp.Optional[Path], **kwargs: tp.Any) -> None:
        """
        Setup the research tool SZZUnleashed with it's code base.

        Args:
            source_folder: location to store the code base in
            **kwargs:
                      * install_prefix
        """
        cfg = vara_cfg()
        if source_folder:
            cfg["szzunleashed"]["source_dir"] = str(source_folder)
        cfg["szzunleashed"]["install_dir"] = str(kwargs["install_prefix"])
        save_config()

        print(f"Setting up SZZUnleashed in {self.source_location()}")

        self.code_base.clone(self.source_location())

    def upgrade(self) -> None:
        """Upgrade the research tool to a newer version."""
        self.code_base.map_sub_projects(lambda prj: prj.pull())

    @staticmethod
    def get_version() -> str:
        """
        Get the current version number of SZZUnleashed.

        Returns:
            the current version number of SZZUnleashed
        """
        with local.cwd(SZZUnleashed.source_location() / "szzunleashed"):
            stdout = gradle("-p", "szz", "properties")
            version_pattern = re.compile("version:\\s+([\\d.]*)")
            match = version_pattern.search(stdout)
            if not match:
                raise AssertionError("Could not determine project version")
            return match.group(1)

    @staticmethod
    def get_jar_name() -> str:
        """
        Get the name of the jar file containing SZZUnleashed.

        Returns:
            the jar file containing SZZUnleashed
        """
        return f"szz_find_bug_introducers-{SZZUnleashed.get_version()}.jar"

    def build(self, build_type: BuildType, install_location: Path) -> None:
        """
        Build SZZUnleashed.

        Args:
            build_type: not used
            install_location: where to put the built jar
        """
        with local.cwd(self.source_location() / "szzunleashed"):
            bb.watch(gradle)("-p", "szz", "build")
            bb.watch(gradle)("-p", "szz", "fatJar")
            bb.watch(cp)(
                f"szz/build/libs/{self.get_jar_name()}",
                str(self.install_location())
            )

    def verify_install(self, install_location: Path) -> bool:
        """
        Verify if SZZUnleashed was correctly installed.

        Returns:
            True, if the tool was correctly installed
        """
        return (install_location / self.get_jar_name()).exists()
