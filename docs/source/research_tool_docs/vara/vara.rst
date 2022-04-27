****
VaRA
****

VaRA is an analysis framework that enables users to build static and dynamic analyses for analyzing high-level concepts using advanced compiler and analysis technology in the background.
Our goal is to enable the user to build these analyses by only focusing on the high-level conceptual information that should be analyzed without worrying about low-level details, such as building complicated compiler modifications or configuring precise but difficult to use static analyses.

The figure below, gives a rough overview of VaRA and the analysis process.
In general, VaRA and our modified clang compiler take as input source code together with high-level conceptual information and either directly analyze it, using various static analyses, or generate an instrumented binary, which can run different dynamic analyses.

.. figure:: VaRA_pipeline_overview.svg

.. raw:: HTML

  <div align="right">
    <a class="reference internal" href="../../index.html#logo-license"
      <span class="std std-ref">CC BY</span>
    </a>
  </div>


Documentation
=============
.. toctree::
   :maxdepth: 2
   :caption: For users:

   setup

.. toctree::
   :maxdepth: 3

   using

.. toctree::
   :maxdepth: 2
   :caption: For developers:

   debugging
   passes

VaRA API Reference
==================
.. toctree::
   :maxdepth: 2

   vara-api/analyses
