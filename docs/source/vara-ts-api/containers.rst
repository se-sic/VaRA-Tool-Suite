Container support
=================

VaRA-TS allows you to :ref:`run experiments in a container <Container Guide>`.
The ``containers`` module handles the correct creation of container images.
Our container images are structured in multiple stages as follows::

    ┌───────────────────────────────────┐  \
    │             Stage 00              │   |
    │ Base Container (e.g., Debian 10)  │   |
    │          + dependencies           │   |
    └───────────────────────────────────┘   |
                      +                     |
    ┌───────────────────────────────────┐   |
    │             Stage 10              │   |
    │         varats/benchbuild         │   |
    └───────────────────────────────────┘   |
                      +                      > Base Image
    ┌───────────────────────────────────┐   |
    │             Stage 20              │   |
    │    Research Tool (e.g., VaRA)     │   |
    └───────────────────────────────────┘   |
                      +                     |
    ┌───────────────────────────────────┐   |
    │             Stage 30              │   |
    │          configuration            │   |
    └───────────────────────────────────┘  /
                      +
    ┌───────────────────────────────────┐
    │         Project Specific          │
    └───────────────────────────────────┘
                      +
    ┌───────────────────────────────────┐
    │        Experiment Specific        │
    └───────────────────────────────────┘


Each stage results in its own container image.
This allows us to update only some of the stages to save time when only changes to certain stages are required (especially stage 00 can be very time consuming to build).
The :ref:`vara-container` tool provides appropriate command line flags to only re-build certain stages.

Base images are built once for each :class:`~varats.containers.containers.ImageBase` with the currently configured research tool using the :ref:`vara-container` tool.
Projects must :ref:`select one of these base images <Using Containers>` which they are then free to extend with their own project-specific dependencies.
The directory structure inside a container looks like the following::

    /
    ├─ app/  # corresponds to the BB build_dir; BB is executed from here
    └─ varats_root/  # corresponds to the varats root directory
       ├─ results/        # mount point to <varats-root>/results outside the container
       ├─ BC_files/       # mount point to <varats-root>/benchbuild/BC_files outside the container
       └─ paper_configs/  # mount point to <varats-root>/paper_configs outside the container

The required mount points are specified automatically when creating a BenchBuild config via :ref:`vara-gen-bbconfig`.

Containers module
.................

.. automodule:: varats.containers.containers
    :members:
    :undoc-members:
    :show-inheritance:
