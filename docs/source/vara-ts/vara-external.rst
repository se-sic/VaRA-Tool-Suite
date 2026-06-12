Managing External Repositories with vara-external
===================================================

**vara-external** is a tool for managing external source repositories that contain custom projects, experiments, research_tools, tables, plots, and reports for the VaRA-TS suite.

Overview
--------

External repositories allow you to extend VaRA-TS with your own **Projects, Experiments, Research Tools,  Tables, Plots and Reports**

Instead of modifying the core VaRA-TS codebase, you can organize your extensions in separate repositories and register them with the tool suite.

Repository Structure
--------------------

External repositories must follow a specific template structure with the required folders placed directly under the repository root:

.. code-block:: text

    your-repository/
    ├── projects/                 # Custom projects
    ├── experiments/              # Custom experiments
    ├── research_tools/           # Custom research_tools
    ├── tables/                   # Custom tables
    ├── plots/                    # Custom plots
    └── reports/                  # Custom reports

**Important:** The repository should contain the required folders directly at its root; **vara-external** detects this layout automatically.

Usage
-----

Register an External Repository
.................................

To register an external repository:

.. code-block:: console

    vara-external set /path/to/your/external-repository

The command will:

1. Validate that the repository follows the required template structure
2. Check that all required folders exist
3. Register the repository path in the VaRA configuration
4. Persist the configuration

**Success Output:**

.. code-block:: console

    Success - External repository configured at: /path/to/your/external-repository

Handle Invalid Repositories
...........................

If the repository structure is invalid:

.. code-block:: console

    Repository Not Complying To Template
      Repository path: /path/to/repo
        Missing or invalid folders:
                - /path/to/repo/projects
                - /path/to/repo/experiments

        Template example: https://github.com/se-sic/varats-oot-template/tree/test-oot
        Expected structure:
            /path/to/repo/projects
            /path/to/repo/experiments
            /path/to/repo/research_tools
            /path/to/repo/tables
            /path/to/repo/plots
            /path/to/repo/reports

Invalid Registered Repositories
...............................

If a previously registered repository becomes invalid (e.g., folders are deleted), **vara-external** will prompt you to confirm unregistering it:

.. code-block:: console

    The repository is already registered but does not match the template. Unregister it from the configuration? [y/N]:

- Type ``y`` to unregister the invalid repository
- Type ``n`` to keep it registered (for recovery/manual cleanup)

Already Registered Repositories
...............................

Attempting to register the same repository twice will skip registration:

.. code-block:: console

    Repository already registered at: /path/to/your/external-repository

Configuration
--------------

Registered external repositories are stored in the VaRA configuration file. The configuration key is:

.. code-block:: yaml

    external_source_repositories = [
        "/path/to/repo1",
        "/path/to/repo2"
    ]

To manually modify registered repositories, edit your VaRA configuration file directly (``$VARATS_ROOT/.varats.yaml``).

Example Workflow
----------------

**Step 1: Clone or fork the template repository**

The easiest way to create an external repository is to start from the official template, which already has the correct nested structure and all required folders.

Clone the template directly:

.. code-block:: console

    git clone https://github.com/se-sic/varats-oot-template.git my-vara-extensions

Or fork it on GitHub and clone your fork for better portability:

.. code-block:: console

    git clone https://github.com/YOUR-USERNAME/varats-oot-template.git my-vara-extensions


**Step 2: Add your custom content**

Navigate to your cloned repository and add your custom projects, experiments, research_tools, tables, plots, and reports to the respective folders:

.. code-block:: console

    cd my-vara-extensions/
    # Add your projects, experiments, etc.

**Step 3: Register with VaRA-TS using vara-external**

Once your repository is ready, register it:

.. code-block:: console

    vara-external set /absolute/path/to/my-vara-extensions

Your custom projects and experiments are now available to VaRA-TS and can be used in experiment configurations.
