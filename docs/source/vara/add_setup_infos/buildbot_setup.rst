Buildbot Setup
==============

Buildbot Master Setup
---------------------

Install Debian Packages
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   sudo apt install libffi-dev libssl-dev

It is very likely that some dependencies are missing here. If you find one, please add it.

Buildbot Master Virtualenv Setup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   sudo su - buildbot-polyjit -s /bin/bash

   python3 -m venv master-env
   source ./master-env/bin/activate

   python3 -m pip install setuptools
   python3 -m pip install buildbot buildbot-console-view buildbot-slave buildbot-waterfall-view buildbot-www
   python3 -m pip install pyOpenSSL pyasn1 pyasn1-modules service-identity
   cd <buildbot-polyjit-repo>
   python3 -m pip install --upgrade -e .

   buildbot upgrade-master <basedir> # 'master' in our case

Workaround for Buildbot Bug
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the file ``master-env/lib/python3.5/site-packages/buildbot/www/auth.py``, insert the following line after line 129:

.. code-block::

   session.user_info = {k: bytes2unicode(v) for k, v in session.user_info.items()}

Buildbot Worker Setup
---------------------

Create a Static ClangFormat Binary
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   # clone necessary repositories
   git clone https://git.llvm.org/git/llvm.git/
   cd llvm/tools
   git clone https://git.llvm.org/git/clang.git/
   cd clang/tools
   git clone https://git.llvm.org/git/clang-tools-extra.git extra

   # compile clang-format
   cd ../../..
   mkdir build
   cd build
   cmake .. -G Ninja -DCMAKE_BUILD_TYPE=MinSizeRel -DLLVM_TARGETS_TO_BUILD=X86 -DLLVM_BUILD_STATIC=true -DLLVM_ENABLE_Z3_SOLVER=OFF
   ninja clang-format

   # static clang-format binary is located at bin/clang-format

Buildbot Worker Setup
---------------------

Create Virtualenv
^^^^^^^^^^^^^^^^^

.. code-block::

   python3 -m venv /path/to/buildbot-worker-venv
   source /path/to/buildbot-worker-venv/bin/activate

   python3 -m pip install buildbot[bundle]

   ## Create Buildbot Worker

   TODO