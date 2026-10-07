"""Auto discover external research tools."""

from pathlib import Path

import varats.utils.external_source_handling as esh
from varats.utils.settings import vara_cfg


def initialize_research_tools() -> None:
    """Initialize builtin and external research tools."""
    # Import builtin tools to trigger automatic registration via
    # __init_subclass__
    from varats.tools.research_tools.phasar import Phasar  # noqa: PLC0415, F401
    from varats.tools.research_tools.szz_unleashed import (  # noqa: PLC0415,F401
        SZZUnleashed,
    )
    from varats.tools.research_tools.vara import VaRA  # noqa: PLC0415, F401

    # Load external research tools from registered repositories
    extra_sources = vara_cfg()['external_source_repositories'].value
    for p in [Path(p) for p in extra_sources]:
        module_folder = p / "research_tools"
        if module_folder.exists():
            esh.load_python_modules_from_external_project(p, module_folder)
