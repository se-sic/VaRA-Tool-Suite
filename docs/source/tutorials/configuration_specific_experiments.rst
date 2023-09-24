Configuration-Specific Experiments
==================================

Modern software projects are often configurable, for example, they allow users to enable or disable specific functionalities or enable them to tune the software for specific use cases.
To study and analyze such configurable software projects, VaRA-TS makes it easy to automatically run an experiment over multiple different configurations of a software project.
Regardless of whether the experiment is built to analyze configuration-specific information or is just a normal experiment, VaRA-TS can automatically multiplex the experiment over a set of configurations.
The produced experiment results are then automatically related to a specific configuration and can, therefore, be interpreted in a configuration-specific way.

* :ref:`Setting up the configuration set`
* :ref:`Analyzing each configuration`
* :ref:`Accessing configuration-specific information`
* :ref:`Configuration-specific results`


Setting up the configuration set
--------------------------------

Manually setting up a small set of configurations that should be analyzed is easy.
One just needs to extend the case-study file of a project with a yaml document that describes the different configurations.

.. code-block:: yaml

  ---
  config_type: PlainCommandlineConfiguration
  0: '["--foo", "--bar"]'
  1: '["--foo"]'
  ...

Afterwards, one needs to specifiy for which revision what configurations should be analyzed by listing the ``config_ids``.

.. code-block:: yaml

  ---
  project_name: FeatureInteractionRepo
  stages:
  - revisions:
    - commit_hash: 1fa18025cfde4adf99c8070ab1d99b930a3b3fe6
      commit_id: 5
      config_ids:
      - 0
      - 1
  version: 0
  ...

In our example, we specify configurations ``0`` and ``1`` to be analyzed for the revision ``1fa18025cfde4adf99c8070ab1d99b930a3b3fe6``.


For larger configuration sets, we recommend an automated approach to generate the configuration set.

TODO: add vara-feature example


Analyzing each configuration
----------------------------

Running an experiment over the set of specified configurations is simple.
We just call :ref:`vara-run` as usual and the framework does the rest.

.. code-block:: console

   vara-run -E RunFeaturePerf FeatureInteractionRepo


This produces one result file for every config id specified.

.. code-block:: console

   results/FeatureInteractionRepo/
   └── FPR-TEF-FeatureInteractionRepo-main-1fa18025cf
       ├── 56a0466a-4ab2-4a4d-a465-4f210e61cd88_config-0_success.zip
       └── 96459028-86aa-48cf-9548-baf13e461018_config-1_success.zip


.. note::

   This only works for projects that are configuration specific.
   If a project wants to be configuration specific it has to specify the :class:`FeatureSource<varats.projects.sources.FeatureSource>` as an additional ``SOURCE``.


Accessing configuration-specific information
--------------------------------------------

During an experiment run, VaRA-TS provides accessor functions to the configuration specific information.
The most basic one is `get_current_config_id`, which returns the config ID during experiment execution.
The configuration-specific information stored in the case study file can be accessed with `get_extra_config_options` which returns a list of configuration options.
For example, to pass the extra configuration options to the exectuion of a command:

.. code-block:: python

   pb_cmd = ... # plumbum command

   extra_options = get_extra_config_options(
       self.project
   )
   with cleanup(prj_command):
       pb_cmd(*extra_options)


Configuration-specific results
------------------------------

Configuration-specific results can be loaded similarly to normal results with `get_processed_revisions_files`.
However, compared to normal files, configuration specific files have their configuration id encoded, which can be queried from the filename.
In cases where it's not clear whether a file name is configuration specific, the method `is_configuration_specific_file` can be used to distinguish normal files from configuration specific ones.
