**************************
How to use VaRA (Overview)
**************************

Overall, VaRA is built for two different usage scenarios:

* Running a static analysis to directly generate analysis result either during compile time or in a post processing step.
* Running a dynamic analysis, by instrumeting the binary during compile time and then later producing the analysis data during execution.

Currently, VaRA implements two high-level concepts and some accompanying analysis pipelines for them, one for analyzing repository meta-data and on for analyzing software features, both are described below in more detail.

* :ref:`Repository Analysis`
* :ref:`Feature Analysis`

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
