Tables
======

Tables provide a simple means to visualize tabular data. VaRA-TS comes with its own table abstraction that uses pandas or `python-tabulate <https://github.com/astanin/python-tabulate>`_ to render tables in different formats.
Here, you can find detailed information about how tables work in VaRA-TS and how to implement your own tables.
For an introduction on how to generate tables see :ref:`this guide <Visualizing Data>`.

Table Architecture
------------------

Tables in VaRA-TS work analogous to plots as described :ref:`here <Plot Architecture>`.
This section applies to tables as well if you replace every occurrence of `plot` with `table`.

How to add a new table in VaRA-TS
---------------------------------

To implement a new plot, you need to create at least one subclass of :class:`~varats.table.tables.TableGenerator` and one :class:`~varats.table.table.Table`.

Each table class must override the abstract function :func:`~varats.table.table.Table.tabulate()` that returns a string of the rendered table.
By convention, the returned string should be produced by `python-tabulate`'s ``tabulate()`` function using the provided ``table_format`` parameter.
There exists also a helper function :func:`~varats.table.table_utils.dataframe_to_table()` that can automatically convert a pandas data frame into the appropriate string representation.
The data for tables should be retrieved using our :ref:`data storage abstraction<Data management>`.

For the table generator, you need to implement the method :func:`~varats.table.table.TableGenerator.generate()`.
The generator's generate function must return one or more instances of table classes that should be generated.
There is no restriction to what tables can be instantiated, but each generator should typically restrict to generating instances of a single table type.


Table helper modules
--------------------

Module: table
.............

.. automodule:: varats.table.table
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: tables
..............

.. automodule:: varats.table.tables
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: table_utils
...................

.. automodule:: varats.table.table_utils
    :members:
    :undoc-members:
    :show-inheritance:
