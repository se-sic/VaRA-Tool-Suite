"""
Setup BenchBuild plugins
"""

from . import projects as __PROJECTS__
from . import plots as __PLOTS__

# Plots need to be discovered before projects because the later loads the
# paper config which in turn can have artifacts that may need to know what
# plots exist.
__PLOTS__.discover()
__PROJECTS__.discover()
