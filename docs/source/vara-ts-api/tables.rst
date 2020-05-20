Tables
======

Tables provide a simple means to visualize tabular data. VaRA-TS comes with its own table abstraction that uses `python-tabulate <https://github.com/astanin/python-tabulate>`_ to render tables in different formats.


How to tabulate your data with VaRA-TS
--------------------------------------

You can create tables for your data either by directly using the :ref:`vara-table` tool, or, if you are working with a :ref:`paper config<How to use paper configs>` and want to automate table generation, you can take a look at :ref:`artefacts`.

How to add a new table in VaRA-TS
---------------------------------

You can create a new table type by creating a subclass of :class:`~varats.tables.table.Table`.
The table will then be available under the name you declare in the class-level field ``NAME``.
Each table class must override the abstract function :func:`~varats.tables.table.Table.tabulate()` that returns a string of the rendered table.
By convention, the returned string should be produced by `python-tabulate`'s ``tabulate()`` function using the table class' :attr:`~varats.tables.table.Table.format` attribute.


Table helper modules
--------------------

Module: table
.............

.. automodule:: varats.tables.table
    :members:
    :undoc-members:
    :show-inheritance:

-----

Module: tables
..............

.. automodule:: varats.tables.tables
    :members:
    :undoc-members:
    :show-inheritance:
