vara-container
==============

This tool is used to manage the container images used when :ref:`running benchbuild in container mode<Running BenchBuild in a container>`.

.. program-output:: vara-container -h
    :nostderr:

This tool provides an easy way to select the research tool that is used in the base containers:

.. program-output:: vara-container select-tool -h
    :nostderr:

With `vara-container build`, you can build all base container images for the current research tool:

.. program-output:: vara-container build -h
    :nostderr:

Existing base images can also be deleted:

.. program-output:: vara-container delete -h
    :nostderr:
