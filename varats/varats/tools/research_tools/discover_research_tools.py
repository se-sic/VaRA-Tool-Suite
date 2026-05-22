"""Auto discover external research tools."""

from pathlib import Path

import varats.utils.external_source_handling as esh
from varats.tools.research_tools.research_tool import ResearchTool
from varats.utils.settings import vara_cfg


def initialize_research_tools() -> None:
    """Initialize builtin and external research tools."""
    # Register builtin tools
    from varats.tools.research_tools.phasar import Phasar
    from varats.tools.research_tools.szz_unleashed import SZZUnleashed
    from varats.tools.research_tools.vara import VaRA

    _builtin_tools = {
        "phasar": Phasar,
        "szzunleashed": SZZUnleashed,
        "vara": VaRA,
    }

    for name, tool_class in _builtin_tools.items():
        if name not in ResearchTool.REGISTRY:
            ResearchTool.REGISTRY[name] = tool_class

    # Load external research tools from registered repositories
    extra_sources = vara_cfg()['external_source_repositories'].value
    for p in [Path(p) for p in extra_sources]:
        module_folder = p / "research_tools"
        if module_folder.exists():
            esh.load_python_modules_from_external_project(p, module_folder)
