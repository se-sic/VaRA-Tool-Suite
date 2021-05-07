Container support
=================

BenchBuild allows you to :ref:`run experiments in a container <Running BenchBuild in a container>`.
The `containers` module handles the correct creation of container images.
Our containers are structured in layers as follows::

    ┌───────────────────────────────────┐  \
    │ Base Container (e.g., Debian 10)  │   |
    └───────────────────────────────────┘   |
                      +                     |
    ┌───────────────────────────────────┐   |
    │              varats               │   |
    └───────────────────────────────────┘   |
                      +                      > Base Image
    ┌───────────────────────────────────┐   |
    │            benchbuild             │   |
    └───────────────────────────────────┘   |
                      +                     |
    ┌───────────────────────────────────┐   |
    │    Research Tool (e.g., VaRA)     │   |
    └───────────────────────────────────┘  /
                      +
    ┌───────────────────────────────────┐
    │         Project Specific          │
    └───────────────────────────────────┘
                      +
    ┌───────────────────────────────────┐
    │        Experiment Specific        │
    └───────────────────────────────────┘


Base images are built once for each :class:`~varats.containers.containers.ImageBase` with the currently configured research tool using the :ref:`vara-container` tool.
Projects must :ref:`select one of these base images <Using Containers>` which they are then free to extend with their own project-specific dependencies.
The directory structure inside a container looks like the following::

    /
    ├─ app/  # corresponds to the BB build_dir; BB is executed from here
    └─ varats_root/  # corresponds to the varats root directory
       ├─ results/        # mount point to <varats-root>/results outside the container
       ├─ BC_files/       # mount point to <varats-root>/benchbuild/BC_files outside the container
       └─ paper_configs/  # mount point to <varats-root>/paper_configs outside the container

See :ref:`Running BenchBuild in a container` for how to set up the mount points.

Containers module
.................

.. automodule:: varats.containers.containers
    :members:
    :undoc-members:
    :show-inheritance:
