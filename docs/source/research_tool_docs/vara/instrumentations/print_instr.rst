Printing Instrumentation (``print``)
====================================

The printing instrumentation is one of the simplest ones, but a great way to debug larger programs.
VaRA inserts at the beginning and end of the program as well as at every start/end of a region a print call that prints the current region's name.

An example output could look like this:

.. code-block:: console

    Init called
    Entering Foo
    << SOME PROGRAM OUTPUT >>
    Leaving Foo
    Entering Bar
    << SOME PROGRAM OUTPUT >>
    Leaving Bar
    Finalize called
