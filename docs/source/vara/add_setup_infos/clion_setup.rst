CLion Setup
===========

How-To Setup VaRA/LLVM in CLion
-------------------------------
- Start CLion
- "Import Project from Sources"
- Select main llvm source directory
- Select "Open existing project" (Important!)
- File -> Settings -> Build,Execution,Deployment -> CMake

   - Create Debug Build
      - Name: ``Debug``
      - Build Type: ``Debug``
      - CMake options:
         .. code-block::

            -DCMAKE_C_FLAGS_DEBUG=
            -DCMAKE_CXX_FLAGS_DEBUG=
            -DLLVM_ENABLE_ASSERTIONS=ON
            -DBUILD_SHARED_LIBS=ON
            -DLLVM_TARGETS_TO_BUILD=X86
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
            -DVARA_BUILD_LIBGIT=ON
            -DLLVM_ENABLE_LLD=ON
            -DLLVM_ENABLE_PROJECTS="clang;lld;compiler-rt;clang-tools-extra;vara;phasar"
            -DCMAKE_INSTALL_PREFIX=~/work/VaRA
      - Environment:
         - ``CFLAGS`` = ``-O2 -g -fno-omit-frame-pointer``
         - ``CXXFLAGS`` = ``-O2 -g -fno-omit-frame-pointer``
      - Generation path: ``build/dev-clion``
      - Build options: ``-j 4`` (or whatever you want)

   - Create Release Build
      - Name: ``Release``
      - Build Type: ``Release``
      - CMake options:
         .. code-block::

            -DCMAKE_C_FLAGS_RELEASE=
            -DCMAKE_CXX_FLAGS_RELEASE=
            -DLLVM_ENABLE_ASSERTIONS=OFF
            -DBUILD_SHARED_LIBS=ON
            -DCMAKE_BUILD_TYPE=Release
            -DLLVM_TARGETS_TO_BUILD=X86
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
            -DVARA_BUILD_LIBGIT=ON
            -DLLVM_ENABLE_LLD=ON
            -DLLVM_ENABLE_PROJECTS="clang;lld;compiler-rt;clang-tools-extra;vara;phasar"
            -DCMAKE_INSTALL_PREFIX=~/work/VaRA
      - Environment:
         - ``CFLAGS`` = ``-O3 -DNDEBUG -march=native -gmlt -fno-omit-frame-pointer``
         - ``CXXFLAGS`` = ``-O3 -DNDEBUG -march=native -gmlt -fno-omit-frame-pointer``
      - Generation path: ``build/opt-clion``
      - Build options: ``-j 4`` (or whatever you want)

- Delete the old build directory cmake-build-debug that was created by clion after the first launch (in the main llvm source directory)
- Add Configuration
   - Add new "Application" configuration
   - Name: ``Build All Targets``
   - Targets: ``All targets``
- If necessary restart CLion or reload CMake (CMake tab -> Reload button)
- Wait until "Building symbols", "Indexing", etc. is done
- Add another application configuration
   - Name: ``Run clang``
   - Targets: ``clang``
   - Executable: ``clang``
   - Program arguments: ``what you want``
   - Working directory: ``what you want``
- Also add configurations with ``clang++/opt`` as target/executable
- You can also create configurations for the targets ``check-vara`` and ``tidy-vara`` for VaRA regression tests and clang-tidy
- Choose configuration ``Build All Targets`` -> ``Build`` button
- You can switch between ``Debug`` and ``Release`` builds in CLion's build configuration drop-down menu
- Done