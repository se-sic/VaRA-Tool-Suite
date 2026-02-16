import os
import typing as tp
from pathlib import Path
from typing import runtime_checkable, Protocol

from varats.project.project_util import ProjectBinaryWrapper
from varats.utils.git_util import ShortCommitHash

BENCHBASE_EXTRA_FILES_DIR: Path = Path(os.path.dirname(__file__)) / 'benchbase'
BENCHBASE_WORKLOAD_CONFIG_DIR: Path = Path(
    os.path.dirname(__file__)
) / 'benchbase' / 'config_templates'


@runtime_checkable
class SupportsBenchbase(Protocol):

    def get_database_name(self) -> str:
        """Get the name of the database associated with this project."""

    def get_benchbase_profile_name(self) -> str:
        """Get the BenchBase profile name for this project."""

    def get_database_connection_string(self) -> str:
        """Get the connection string for the database associated with this
        project."""

    def database_binary(
        self, revision: ShortCommitHash
    ) -> ProjectBinaryWrapper:
        """Get the binary used to interact with the database associated with
        this project."""

    def start_database_server(self) -> None:
        """Start the database server."""

    def stop_database_server(self) -> None:
        """Stop the database server."""

    def render_workload_config(
        self, workload: str, configuration: tp.Dict[str, tp.Union[bool, str]]
    ) -> Path:
        """Render the workload configuration for BenchBase."""
