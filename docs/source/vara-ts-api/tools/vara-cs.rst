vara-cs
=======

This tool provides functionality to create and manage
:ref:`case studies<Module: case_study>`.
Detailed information about how case studies work can be found :ref:`here<How to use case studies>`.

The `vara-cs` tool has various sub-commands which we explain in more detail
below:

.. program-output:: vara-cs --help
    :nostderr:


vara-cs gen
-----------

The ``vara-cs gen`` command generates a new or extends a existing one case study.
Which revisions are added to the case study depends on the chosen *selection strategy*.
New case studies are automatically inserted into the current paper config.

For more options, take a look at the command line parameters:

.. program-output:: vara-cs gen --help
    :nostderr:


vara-cs status
--------------

The ``vara-cs status`` command prints status information about the results
of your experiments.
It can give an overview over the status of all case studies or more detailed
information about specific case studies.

.. program-output:: vara-cs status --help
    :nostderr:


vara-cs package
---------------

The ``vara-cs package`` command allows to package all files belonging to the
current paper config into a ``.zip`` file.

.. program-output:: vara-cs package --help
    :nostderr:


vara-cs view
-------------

The ``vara-cs view`` command allows to easily open result files in your favourite editor.
The tool searches for result files matching the given commit hash and presents you a list with the found files.
The selected file then gets opened using the program in your ``EDITOR`` environment variable.

.. program-output:: vara-cs view --help
    :nostderr:


vara-cs cleanup
---------------

The ``vara-cs cleanup`` command allows the user to easily remove old or no longer wanted report files.

.. program-output:: vara-cs cleanup --help
    :nostderr:
