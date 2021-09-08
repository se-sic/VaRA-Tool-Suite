Build VaRA with vara-buildsetup
===============================

:ref:`vara-buildsetup` is the tool used to install and build VaRA.


Installation
------------

Install dependencies
********************

To use the VaRA Tool Suite, your system has to have at least `python3.7`. Make sure you have the necessary packages installed.

For ubuntu:

.. code-block:: console

    sudo apt install python3-dev python3-tk python3-psutil psutils ninja-build python3-pip autoconf cmake ruby curl time libyaml-dev
    sudo apt install python3-venv # If you want to install VaRA-TS in a python virtualenv

For arch:

.. code-block:: console

    sudo pacman -Syu --needed python tk python-psutil psutils ninja python-pip python-statsmodels autoconf cmake ruby curl time libyaml python-coverage

Get the source
**************

First you will need to clone the VaRA Tool Suite repository.

.. code-block:: console

    export VARA_ROOT="$HOME/vara" # or something else
    cd "$VARA_ROOT"
    git clone git@github.com:se-passau/VaRA-Tool-Suite.git
    cd VaRA-Tool-Suite


Install to python user-directory (easier)
*****************************************

The simplest way to install VaRA-TS is by using pip.

.. code-block:: console

    pip3 install varats

To install VaRA-TS from the repository into the user directory use the
following command.  The same command can be used to update an existing
installation (if necessary).

.. code-block:: console

    # cd to VaRA-TS directory
    python3 -m pip install --user --upgrade -e ./varats-core
    python3 -m pip install --user --upgrade -e ./varats

    # developers also need to execute the next command
    # (if you want to contribute to VaRA/VaRA-TS):
    python3 -m pip install -r requirements.txt

This initializes `VaRA-TS` and installs the `vara-graphview` tool to visualize VaRA results.

Install to python virtualenv (advanced)
***************************************

.. code-block:: console

    # create virtualenv
    python3 -m venv /where/you/want/your/virtualenv/to/live

    # activate virtualenv
    source /path/to/virtualenv/bin/activate

    # cd to VaRA-TS directory
    python3 -m pip install --upgrade -e ./varats-core
    python3 -m pip install --upgrade -e ./varats

    # developers also need to execute the next command
    # (if you want to contribute to VaRA/VaRA-TS):
    python3 -m pip install -r requirements.txt

The virtualenv method has the advantage that it does not mess with your local python user
directory. With this method you have to execute the `source` command every time before
you can execute the `vara-graphview` program.

Usage
-----

Install VaRA
************

Required system dependencies for building VaRA.

.. code-block:: console

    sudo apt install libsqlite3-dev libcurl4-openssl-dev libboost-all-dev libpapi-dev googletest libxml2-dev

The following example shows how to setup VaRA via command line.

.. code-block:: console

    mkdir $VARA_ROOT
    cd $VARA_ROOT
    vara-buildsetup vara -i
    vara-buildsetup vara -b

Update VaRA
***********

Updating VaRA to a new version can also be done with `vara-buildsetup`.

.. code-block:: console

    vara-buildsetup vara -u
    vara-buildsetup vara -b

Upgrading VaRA
**************

To upgrade VaRA to a new release, for example, `release_70`, use:

.. code-block:: console

    vara-buildsetup vara -u --version 110

Debugging
---------

Per default, `vara-buildsetup` doesn't provide debug output. When working on VaRA, it
is helpful to get some debug output when building it. For example to know, if the current
build fails.

To get debug output set the `LOG_LEVEL` environment variable to `debug`.

.. code-block:: console

    # for the entire section
    export LOG_LEVEL=devel

    # just then running vara-buildsetup
    LOG_LEVEL=debug vara-buildsetup vara -b

Post-installation
-----------------

After having compiled VaRA, update the `PATH` and `LD_LIBRARY_PATH` environment variables to
use the just compiled VaRA build instead of your system clang install.

.. code-block:: console

    export LD_LIBRARY_PATH=$VARA_ROOT/tools/VaRA/lib:$LD_LIBRARY_PATH
    export PATH=$VARA_ROOT/tools/VaRA/bin:$PATH
