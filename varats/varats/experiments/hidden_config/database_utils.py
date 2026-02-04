import os
import typing as tp
from pathlib import Path

from typing_extensions import runtime_checkable, Protocol

from varats.project.project_util import ProjectBinaryWrapper


@runtime_checkable
class SupportsBenchbase(Protocol):
    BENCHBASE_WORKLOAD_CONFIG_DIR: Path = Path(
        os.path.dirname(__file__)
    ) / 'benchbase_config_templates'

    def get_database_name(self) -> str:
        """Get the name of the database associated with this project."""
        ...

    def get_benchbase_profile_name(self) -> str:
        """Get the BenchBase profile name for this project."""
        ...

    def get_database_connection_string(self) -> str:
        """Get the connection string for the database associated with this
        project."""
        ...

    def database_binary(self) -> ProjectBinaryWrapper:
        """Get the binary used to interact with the database associated with
        this project."""
        ...

    def start_database_server(self) -> None:
        """Start the database server."""
        ...

    def stop_database_server(self) -> None:
        """Stop the database server."""
        ...

    def render_workload_config(
        self, workload: str, configuration: tp.Map[str, tp.Union[bool, str]]
    ) -> Path:
        ...
