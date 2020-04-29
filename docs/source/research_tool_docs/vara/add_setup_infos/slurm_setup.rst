Running with Slurm
==================

This page describes how benchbuild/VaRA experiments can be run on the chair's cluster using slurm.

As no home directories are not available on the cluster nodes, you must use ``scratch`` instead.
Setup up a ``virtualenv`` with the tool suite on scratch.

.. code-block:: bash

  cd /scratch/<user>/
  virtualenv -p /usr/bin/python3 vara-virt

Furthermore, this guide assumes that your vara-root directory is ``/scratch/<user>/vara``.

.. code-block::

   cd /scratch/<user>/vara

1. Clone Tool-Suite and set up VaRA

   | We assume that VaRA is installed to ``/scratch/<user>/vara/VaRA``

2. Edit ``.vara.yaml`` and set options:

.. code-block::

   - result_dir: /scratch/<user>/vara/results
   - paper_config:
     - current_config: <your_config>
     - folder: /scratch/<user>/vara/paper_configs

3. | Create benchbuild config (``vara-gen-bbconfig``)

4. Edit benchbuild config (``/scratch/<user>/vara/benchbuild/.benchbuild.yml``) as needed:

   - set benchbuild directories to point to scratch:

   .. code-block::

      build_dir:
         value: /scratch/<user>/vara/benchbuild/results
      tmp_dir:
         value: /scratch/<user>/vara/benchbuild/tmp

   - set environment variables to point to scratch:

   .. code-block::

      env:
        value:
            PATH:
            - /scratch/<user>/vara/VaRA/bin/
            HOME: /scratch/<user>/

   - configure slurm related parameters:

   .. code-block::

      jobs: '10' # TODO: find good default
      parallel_processes: '4' # TODO: find good default

      slurm:
          account:
              value: ls-apel
          partition:
              value: anywhere # or name of the cluster to run on
          timelimit:
              value: 'hh:mm:ss'

   - set vara related options:

   .. code-block::

      vara:
          outfile: /scratch/<user>/vara/results
          result: BC_files

   - increase verbosity

   .. code-block::

      verbosity:
        value: <0-4>

5. Generate bb script

    .. note::

      Activate your virtualenv to use the correct benchbuild

   .. code-block::

      benchbuild slurm -E <report_type> <project>

   Move resulting script to appropriate subdir, e.g.:

   .. code-block::

      mv <report_type>-slurm.sh bb-configs/<report_type>-slurm-<project>.sh

6. (Optional) Modify -o parameter of SBATCH to get output file for debugging, e.g.

   .. code-block::

      #SBATCH -o /scratch/<user>/vara/benchbuild/slurm-output/cs-overview/doxygen/GitBlameAnnotationReport-%A_%a.txt

7. Start a job:

   .. code-block::

      cd benchbuild

      sbatch bb-configs/<report_type>-slurm-<project>.sh
      # or
      sbatch --constraint=kine bb-configs/<report_type>-slurm-<project>.sh

NOTE: If you want to run the same project again (with GitBlameAnnotationReport), you need to empty the BC_files directory, because the path to the git repository will be different. See `#494 <https://github.com/se-passau/VaRA/issues/494>`_

To use interaction filters, I recommend storing all of them in a separate directory (e.g., benchbuild/interaction_filters) with descriptive names and symlinking them to the place where the experiment expects them.

TIP: In case you get strange errors or results, try to empty all temporary directories and try again, e.g.:

      - benchbuild/BC_files
      - benchbuild/results
      - benchbuild/tmp_dir
      - data_cache

Handling Missing Dependencies for VaRA
--------------------------------------

If certain libraries needed by vara or clang are missing on the slurm-nodes, you can bring them yourself:

1. Create a folder for the libraries on scratch

   .. code-block::

      mkdir /scratch/<username>/vara/libs

2. | Copy the necessary libraries from your system to the libs folder

3. Add the following entry to the ``env`` section of your benchbuild config:

   .. code-block::

      env:
          value:
              LD_LIBARARY_PATH:
              - /scratch/<user>/vara/libs
