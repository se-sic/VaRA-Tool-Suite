"""Utilities for tool handling."""

import typing as tp
from functools import wraps
from pathlib import Path

from varats.tools.research_tools.phasar import Phasar
from varats.tools.research_tools.research_tool import ResearchTool
from varats.tools.research_tools.vara import VaRA
from varats.utils.exceptions import ConfigurationLookupError
from varats.utils.settings import vara_cfg


def get_research_tool_type(
    name: str
) -> tp.Union[tp.Type[VaRA], tp.Type[Phasar]]:
    """
    Look up the type of a research tool by name.

    Args:
        name: of the research tool

    Returns: the research tool type corresponding to ``name``
    """
    if name in ("VaRA", "vara"):
        return VaRA

    if name == "phasar":
        return Phasar

    raise LookupError(f"Could not find research tool {name}")


def get_research_tool(
    name: str,
    source_location: tp.Optional[Path] = None
) -> ResearchTool[tp.Any]:
    """
    Look up a research tool by name.

    Args:
        name: of the research tool
        source_location: of the research tool, if ``None`` is provided the
                         location saved in the config will be used

    Returns:
        the research tool with the specified ``name``,
        otherwise, raises LookupError
    """
    rs_type = get_research_tool_type(name)

    if source_location:
        src_folder = Path(source_location)
    elif rs_type.has_source_location():
        src_folder = rs_type.source_location()
    else:
        config_root_path = Path(str(vara_cfg()["config_file"])).parent
        src_folder = config_root_path / "tools_src/"

    if not src_folder.exists():
        src_folder.mkdir(parents=True)

    return rs_type(src_folder)


def get_supported_research_tool_names() -> tp.List[str]:
    """Returns a list of all supported research tools."""
    return ["phasar", "vara"]


def configuration_lookup_error_handler(func: tp.Any) -> tp.Any:
    """Wrapper for drivers to catche internal Exceptions and provide a helpful
    message to the user."""

    @wraps(func)
    def wrapper_configuration_lookup_error_handler(
        *args: tp.Any, **kwargs: tp.Any
    ) -> tp.Any:
        try:
            func(*args, *kwargs)
        except ConfigurationLookupError:
            print(
                "No paper config was set. "
                "To create or select a paper config use vara-pc"
            )

    return wrapper_configuration_lookup_error_handler
