**************************
How to use VaRA (Overview)
**************************

Overall, VaRA is built for two different usage scenarios:

* Running a static analysis to directly generate analysis result either during compile time or in a post processing step.
* Running a dynamic analysis, by instrumeting the binary during compile time and then later producing the analysis data during execution.

Currently, VaRA implements two high-level concepts and some accompanying analysis pipelines for them, one for analyzing repository meta-data and on for analyzing software features, both are described below in more detail.

* :ref:`Highlight Analysis`
* :ref:`Repository Analysis`
* :ref:`Feature Analysis`


Highlight Analysis
==================

.. toctree::
   :maxdepth: 1

   regions/highlight_region
   usages/highlight_analysis


Repository Analysis
===================

.. toctree::
   :maxdepth: 1

   usages/commit_interaction_analysis


Feature Analysis
================

.. toctree::
   :maxdepth: 1

   usages/feature_performance_analysis


Instrumentations
================

VaRA can automatically add instrumentation code around detected regions.
To enable this, specify a region detection strategy, enable the tracing code with ``CXX_FLAGS += -fsanitize=vara`` and specify the wanted instrumention code with ``-fvara-instr=INSTR_TYPE``.


.. toctree::
   :maxdepth: 1

   instrumentations/print_instr
   instrumentations/clock_instr.rst
   instrumentations/trace_event_instr.rst
   instrumentations/instr_verify.rst
   instrumentations/usdt.rst
