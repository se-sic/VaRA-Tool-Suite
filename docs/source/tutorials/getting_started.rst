Getting Started
===============

Installing VaRA Tool-Suite
--------------------------

To use the VaRA Tool-Suite, your system has to have at least `python3.7`. Make sure you have the necessary packages installed.

For ubuntu:

.. code-block:: console

    sudo apt install python3-dev python3-tk python3-psutil psutils ninja-build python3-pip autoconf cmake ruby curl time libyaml-dev git graphviz-dev
    sudo apt install python3-venv # If you want to install VaRA-TS in a python virtualenv

For arch:

.. code-block:: console

    sudo pacman -Syu --needed python tk python-psutil psutils ninja python-pip python-statsmodels autoconf cmake ruby curl time libyaml python-coverage graphviz

We recommend to use a virtual environment to install VaRA-TS.

.. code-block:: console

    # create virtualenv
    python3 -m venv /where/you/want/your/virtualenv/to/live

    # activate virtualenv
    source /path/to/virtualenv/bin/activate

The simplest way to install VaRA-TS is by using pip.

.. code-block:: console

    pip3 install varats


Post Install Steps
------------------

After a successful install, we need to create a proper environment to run experiments in.
First, we need to select a directory where we create our setup.
From now on, we refer to this directory as the `VaRA-TS root`.
**Unless noted otherwise,** ``vara-*`` **commands should always be run from this directory.**

.. code-block:: console

    mkdir $VARATS_ROOT
    cd $VARATS_ROOT

    # create config files
    vara-gen-bbconfig

This should generate the VaRA-TS config file as ``.varats.yaml`` as well as a BenchBuild config file ``benchbuild/.benchbuild.yml``.

You are now ready to :ref:`run your first experiment <Running Experiments>`.

.. hint:: You should also take a look at the other :ref:`tools <Tools Overview>`, which are offered by varats.
