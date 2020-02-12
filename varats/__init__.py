"""
Setup BenchBuild plugins
"""

from . import projects as __PROJECTS__
from . import plots as __PLOTS__

__PROJECTS__.discover()
__PLOTS__.discover()
