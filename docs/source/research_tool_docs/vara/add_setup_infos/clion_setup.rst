CLion Setup
===========

How to set up VaRA/LLVM in CLion
--------------------------------
1. Use ``vara-buildsetup vara -i`` to correctly clone and checkout the VaRa/LLVM repos (cf. :ref:`How to setup VaRA`)

2. Start CLion and from the menu select **File | Open** and point to ``<varats_root>/tools_src/vara-llvm-project/llvm/CMakeLists.txt``.
   In the dialog that opens, click **Open as Project**.

3. Go to **Settings/Preferences | Build, Execution, Deployment | CMake** to configure the CMake project.
   Use the **+** symbol to create a new profile and adjust the settings as follows and confirm with **Ok** once you are done:

   - Debug/Dev build:
      - **Name:** Debug (or Dev)
      - **Build type:** Debug
      - **Toolchain:** Default  (make sure that your toolchain is configured to use clang)
      - **CMake options:**
        .. code-block::

           -DBUILD_CLAR=OFF
           -DBUILD_SHARED_LIBS=ON
           -DCMAKE_C_FLAGS_DEBUG="-O2 -g -fno-omit-frame-pointer"
           -DCMAKE_CXX_FLAGS_DEBUG="-O2 -g -fno-omit-frame-pointer"
           -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--undefined-version"
           -DCMAKE_CXX_STANDARD=17
           -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
           -DCMAKE_INSTALL_PREFIX=<varats_root>/tools/VaRA
           -DLLVM_ENABLE_ASSERTIONS=ON
           -DLLVM_ENABLE_BINDINGS=OFF
           -DLLVM_ENABLE_EH=ON
           -DLLVM_ENABLE_LLD=ON
           -DLLVM_ENABLE_PROJECTS="clang;lld;compiler-rt;clang-tools-extra;vara;phasar"
           -DLLVM_ENABLE_RTTI=ON
           -DLLVM_OPTIMIZED_TABLEGEN=ON
           -DLLVM_PARALLEL_LINK_JOBS=4
           -DLLVM_PHASAR_BUILD=ON
           -DLLVM_TOOL_PHASAR_BUILD=ON
           -DPHASAR_ENABLE_DYNAMIC_LOG=OFF
           -DPHASAR_BUILD_IR=OFF
           -DPHASAR_BUILD_UNITTESTS=OFF
           -DLLVM_TARGETS_TO_BUILD=X86
           -DLLVM_TOOL_PHASAR_BUILD=ON
           -DUSE_HTTPS=OFF
           -DUSE_SSH=OFF
           -DVARA_BUILD_LIBGIT=ON
           -DVARA_FEATURE_BUILD_PYTHON_BINDINGS=OFF
           -DVARA_FEATURE_BUILD_Z3_SOLVER=ON
           -DVARA_FEATURE_USE_Z3_SOLVER=ON

        Use ``-O0`` for debug builds and ``-O2`` for development builds.

      - **Build directory:** ``<varats_root>/tools_src/vara-llvm-project/build/dev-clion``
      - **Build options:** leave empty

   - Release Build
      - **Name:** Release
      - **Build type:** Release
      - **Toolchain:** Default  (make sure that your toolchain is configured to use clang)
      - **CMake options:**
        .. code-block::

           -DBUILD_CLAR=OFF
           -DBUILD_SHARED_LIBS=ON
           -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG -march=native -fno-omit-frame-pointer -gmlt"
           -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -march=native -fno-omit-frame-pointer -gmlt"
           -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--undefined-version"
           -DCMAKE_CXX_STANDARD=17
           -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
           -DCMAKE_INSTALL_PREFIX=<varats_root>/tools/VaRA
           -DLLVM_ENABLE_ASSERTIONS=OFF
           -DLLVM_ENABLE_BINDINGS=OFF
           -DLLVM_ENABLE_EH=ON
           -DLLVM_ENABLE_LLD=ON
           -DLLVM_ENABLE_PROJECTS="clang;lld;compiler-rt;clang-tools-extra;vara;phasar"
           -DLLVM_ENABLE_RTTI=ON
           -DLLVM_OPTIMIZED_TABLEGEN=ON
           -DLLVM_PARALLEL_LINK_JOBS=4
           -DLLVM_PHASAR_BUILD=ON
           -DLLVM_TOOL_PHASAR_BUILD=ON
           -DPHASAR_ENABLE_DYNAMIC_LOG=OFF
           -DPHASAR_BUILD_IR=OFF
           -DPHASAR_BUILD_UNITTESTS=OFF
           -DLLVM_TARGETS_TO_BUILD=X86
           -DLLVM_TOOL_PHASAR_BUILD=ON
           -DUSE_HTTPS=OFF
           -DUSE_SSH=OFF
           -DVARA_BUILD_LIBGIT=ON
           -DVARA_FEATURE_BUILD_PYTHON_BINDINGS=OFF
           -DVARA_FEATURE_BUILD_Z3_SOLVER=ON
           -DVARA_FEATURE_USE_Z3_SOLVER=ON

      - **Build directory:** ``<varats_root>/tools_src/vara-llvm-project/build/dev-clion``
      - **Build options:** leave empty

4. Call **Tools | CMake | Change Project Root** from the main menu and select the top-level repository folder, ``vara-llvm-project`` to see the entire repository in the Project tree.

5. Delete the old build directory ``llvm/cmake-build-debug`` that was created by clion after the first launch

6. Build the project using **Build | Build Project**

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
