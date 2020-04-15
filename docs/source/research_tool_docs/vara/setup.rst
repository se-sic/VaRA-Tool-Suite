How to setup VaRA
=================
This is a quick guide on how to setup VaRA either with our automatic setup or manually.

Manual Installation
-------------------
VaRA can be automatically set up with :ref:`vara-buildsetup` from the tool suite, for instructions see setup.
If you want to manually install llvm and VaRA see the following instructions.

Linux
.....
To create your own setup or integrate VaRA into LLVM follow these instructions.
First, clone our modified version of `llvm's monorepo <https://github.com/se-passau/vara-llvm-project>`_ or patch our modifications into your version of llvm-project.

.. code-block:: bash

  cd where-you-want-llvm-to-live
  git clone git@github.com:se-passau/vara-llvm-project.git vara-llvm-project
  cd vara-llvm-project
  git submodule init && git submodule update --recursive

Second, checkout the VaRA repository as ``vara`` into ``vara-llvm-project``.

.. code-block:: bash

  git clone https://github.com/se-passau/VaRA.git vara
  git submodule init && git submodule update --recursive

Third, to complete the setup link the prepared VaRA build scripts into a build folder.

.. code-block:: bash

  cd vara-llvm-project
  mkdir build
  ln -s vara/utils/vara/builds build/build_cfg

After the setup, you find prepared build scripts in the build folder to automatically configure a llvm + vara.

.. code-block:: bash

  cd vara-llvm-project/build
  ./build_cfg/build-{TYPE}.sh
  cd {TYPE}
  cmake --build .

.. code-block:: bash

  builds
     ├── build-opt.sh                           # Normal, optimized release build
     ├── build-dev.sh                           # Development build
     ├── build-dev-san.sh                       # Development build with ASAN and UBSAN
     ├── build-dbg.sh                           # Special debug build with extra debug info
     └── build-PGO.sh                           # Clang PGO bootstrap [Experimental]

.. toctree::
    :maxdepth: 1
    :caption: Additional setup information

    add_setup_infos/clion_setup
    add_setup_infos/slurm_setup
    add_setup_infos/buildbot_setup
    add_setup_infos/python_scripting_tips
