CLion Setup
===========

How to set up VaRA/LLVM in CLion
--------------------------------
1. Use ``vara-buildsetup vara -i`` to correctly clone and checkout the VaRa/LLVM repos (cf. :ref:`How to setup VaRA`)

2. Start CLion and from the menu select **File | Open** and point to ``<varats_root>/vara-llvm-project/llvm/CMakeLists.txt``.
   In the dialog that opens, click **Open as Project**.

3. Go to **Settings/Preferences | Build, Execution, Deployment | CMake** to configure the CMake project.
   Use the **+** symbol to create a new profile and adjust the settings as follows and confirm with **Ok** once you are done:

   - Debug build:
      - **Name:** Debug
      - **Build type:** Debug
      - **Toolchain:** Default  (make sure that your toolchain is configured to use clang)
      - **CMake options:**
        .. code-block::

           -DBUILD_SHARED_LIBS=ON
           -DLLVM_TARGETS_TO_BUILD=X86
           -DLLVM_USE_NEWPM=ON
           -DLLVM_ENABLE_LDD=ON
           -DLLVM_PARALLEL_LINK_JOBS=4
           -DCMAKE_C_FLAGS_DEBUG=
           -DCMAKE_CXX_FLAGS_DEBUG=
           -DLLVM_ENABLE_ASSERTIONS=ON
           -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
           -DLLVM_OPTIMIZED_TABLEGEN=ON
           -DLLVM_PHASAR_BUILD=ON
           -DLLVM_TOOL_PHASAR_BUILD=ON
           -DLLVM_ENABLE_RTTI=ON
           -DLLVM_ENABLE_EH=ON
           -DVARA_BUILD_LIBGIT=ON
           -DUSE_HTTPS=OFF
           -DUSE_SSH=OFF
           -DBUILD_CLAR=OFF
           -DLLVM_ENABLE_PROJECTS="clang;lld;compiler-rt;clang-tools-extra;vara;phasar"
           -DCMAKE_CXX_STANDARD=17
           -DLLVM_ENABLE_BINDINGS=OFF
           -DCMAKE_INSTALL_PREFIX=<varats_root>/tools/VaRA

      - **Build directory:** ``<varats_root>/tools_src/vara-llvm-project/build/dev-clion``
      - **Build options:** ``-j 4`` (leave as-is to use all available cores)
      - **Environment:**
         - ``CFLAGS=-O2 -g -fno-omit-frame-pointer``
         - ``CXXFLAGS=-O2 -g -fno-omit-frame-pointer``

   - Release Build
      - **Name:** Release
      - **Build type:** Release
      - **Toolchain:** Default  (make sure that your toolchain is configured to use clang)
      - **CMake options:**
        .. code-block::

           -DBUILD_SHARED_LIBS=ON
           -DLLVM_TARGETS_TO_BUILD=X86
           -DLLVM_USE_NEWPM=ON
           -DLLVM_ENABLE_LDD=ON
           -DLLVM_PARALLEL_LINK_JOBS=4
           -DCMAKE_C_FLAGS_RELEASE=
           -DCMAKE_CXX_FLAGS_RELEASE=
           -DLLVM_ENABLE_ASSERTIONS=OFF
           -DLLVM_PHASAR_BUILD=ON
           -DLLVM_TOOL_PHASAR_BUILD=ON
           -DLLVM_ENABLE_RTTI=ON
           -DLLVM_ENABLE_EH=ON
           -DVARA_BUILD_LIBGIT=ON
           -DUSE_HTTPS=OFF
           -DUSE_SSH=OFF
           -DBUILD_CLAR=OFF
           -DLLVM_ENABLE_PROJECTS="clang;lld;compiler-rt;clang-tools-extra;vara;phasar"
           -DCMAKE_CXX_STANDARD=17
           -DLLVM_ENABLE_BINDINGS=OFF
           -DCMAKE_INSTALL_PREFIX=<varats_root>/tools/VaRA

      - **Build directory:** ``<varats_root>/tools_src/vara-llvm-project/build/dev-clion``
      - **Build options:** ``-j 4`` (leave as-is to use all available cores)
      - **Environment:**
         - ``CFLAGS=-O3 -DNDEBUG -march=native -fno-omit-frame-pointer -gmlt``
         - ``CXXFLAGS=-O3 -DNDEBUG -march=native -fno-omit-frame-pointer -gmlt``

4. Call **Tools | CMake | Change Project Root** from the main menu and select the top-level repository folder, ``vara-llvm-project`` to see the entire repository in the Project tree.

5. Delete the old build directory ``llvm/cmake-build-debug`` that was created by clion after the first launch

6. Build the project using **Build | Build Project**

   You can also create a run configuration that builds the project:
       - Add a new "CMake Application" configuration
       - Name: ``Build All Targets``
       - Targets: ``All targets``

(This guide follows the section `Work with a monorepo <https://www.jetbrains.com/help/clion/creating-new-project-from-scratch.html#monorepos>`_ in the official CLion documentation)


Running applications within CLion
---------------------------------

To run VaRA from within clion, you need to create `run configurations <https://www.jetbrains.com/help/clion/run-debug-configuration.html#createExplicitly>`_.
Choose **CMake Application** as a template and select the **Targets** and **Executable** depending on the application you want to run (e.g., `clang`, `clang++`, or `opt`).
The targets ``check-vara`` and ``tidy-vara`` execute the VaRA regression tests and clang-tidy checks.


Tips & Tricks
-------------

Changes to the CMake project do not apply automatically
#######################################################

You can manually reload the CMake project via the reload button in the CMake tab.

Code completion or highlighting does not work
#############################################

Wait until `Building symbols`, `Indexing`, etc. is done or reload the CMake project.

The debugger does stop at breakpoints and doesn't show the source code.
#######################################################################

This is most likely because the build does not include debugging symbols. Check if you have selected the ``Debug`` configuration for the build. If it doesn't work even if you used the debug configuration, the problem might disappear if you clean the build directory (e.g., **Build | Clean**) and reload the CMake project.
