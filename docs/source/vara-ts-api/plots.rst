Plots
=====

Plots are used to visualize data from one or more reports.
VaRA-TS comes with its own plot abstraction that uses pyplot, seaborn and similar for plotting, which can tie plot and research data together to be automatically generated.


How to plot your data with VaRA-TS
----------------------------------

You can plot your data either by directly using the :ref:`vara-plot` tool, or if you are working with a :ref:`paper config<How to use paper configs>` and want to automate plot generation, take a look at :ref:`artefacts`.

How to add a new plot in VaRA-TS
--------------------------------

You can create a new plot by creating a subclass of :class:`~varats.plots.plot.Plot`.
The plot will then be available under the name you declare in the class-level field ``NAME``.
Each plot class must override the abstract function :func:`~varats.plots.plot.Plot.plot()` that is responsible for generating the plot, as well as the abstract function :func:`~varats.plots.plot.Plot.show()` that is called when the plot sould only displayed, but not saved.
The latter usually consists of a call `self.plot()`, followed by a call to `pyplot.show()`.

The data for plots should be retrieved using our :ref:`data storage abstraction<Data management>`.

Plot helper modules
-------------------

Module: plot
............

.. automodule:: varats.plots.plot
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: plot_utils
..................

.. automodule:: varats.plots.plot_utils
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: plots
.............

.. automodule:: varats.plots.plots
    :members:
    :undoc-members:
    :show-inheritance:
