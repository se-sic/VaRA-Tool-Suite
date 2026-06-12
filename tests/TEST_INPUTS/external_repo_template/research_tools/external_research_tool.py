"""Dummy external research tool for registry tests."""

from pathlib import Path

from varats.tools.research_tools.research_tool import (
    Dependencies,
    ResearchTool,
)
from varats.tools.research_tools.vara_manager import BuildType


class ExternalResearchTool(ResearchTool[object]):
    """Dummy external research tool."""

    @classmethod
    def get_dependencies(cls) -> Dependencies:
        return Dependencies({})

    @staticmethod
    def source_location() -> Path:
        return Path(".")

    @staticmethod
    def has_source_location() -> bool:
        return True

    @staticmethod
    def install_location() -> Path:
        return Path(".")

    @staticmethod
    def has_install_location() -> bool:
        return True

    def setup(
        self, source_folder: Path | None, install_prefix: Path,
        version: int | None
    ) -> None:
        return None

    def find_highest_sub_prj_version(self, sub_prj_name: str) -> int:
        return 0

    def is_up_to_date(self) -> bool:
        return True

    def upgrade(self) -> None:
        return None

    def build(
        self, build_type: BuildType, install_location: Path,
        build_folder_suffix: str | None
    ) -> None:
        return None

    def get_install_binaries(self) -> list[str]:
        return []

    def verify_build(
        self, build_type: BuildType,
        build_folder_suffix: str | None
    ) -> bool:
        return True
