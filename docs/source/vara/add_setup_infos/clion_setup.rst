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

`TODO (se-passau/VaRA#569) <https://github.com/se-passau/VaRA/issues/569>`_: write docs
