******
PhASAR
******

PhASAR is a LLVM-based Static Analysis Framework which can be found `on GitHub <https://github.com/secure-software-engineering/phasar>`__.

What is Phasar?
---------------
Phasar is a LLVM-based static analysis framework written in C++. It allows users to specify arbitrary data-flow problems which are then solved in a fully-automated manner on the specified LLVM IR target code. Computing points-to information, call-graph(s), etc. is done by the framework, thus you can focus on what matters.

Install PhASAR with VaRA
------------------------
The following bash script creates a vara-root directory and installs PhASAR in it.

.. code-block:: console

    #!/bin/bash
    # Create and enter vara-root
    mkdir -p vara-root && vara-root
    # Create PhASAR config directory
    mkdir -p /home/$USER/.config/phasar
    chown -R $USER:$USER /home/$USER/.config/phasar
    # Get PhASAR
    vara-buildsetup phasar -i
    # Build PhASAR
    vara-buildsetup phasar -b
