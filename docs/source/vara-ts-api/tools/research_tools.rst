Research Tools
==============

.. toctree::
   :maxdepth: 1
   :caption: List of provided research tools:

   research_tools/vara


Research Tool API
-----------------
VaRA-TS offers an abstraction to implement research tools that makes it easy to add a new tool and automatically deploy it, and it's experiments, via the tool suite.
To add a new research tool one has to implement to classes.
The research tool it self must inherit from ``ResearchTool`` and implement the specified abstract methods to setup, upgrade, build, and install the research tool.
In addition, one needs to implement a ``CodeBase`` to specify the repository layout of the research tools code.
The ``CodeBase`` makes it convenient to interact with the, possible multiple, repository of a research tool to setup and manage the code.
Furthmore, the tool suite provides different helper function an services that depend on the ``CodeBase`` abstraction, e.g., :ref:`vara-develop`.

.. automodule:: varats.tools.research_tools.research_tool
    :members:
    :undoc-members:
    :show-inheritance:
