# VaRA Tool Suite

## Project Status [![Codacy Badge](https://api.codacy.com/project/badge/Grade/a52d7d5380a24733b2540e0f6d8a6112)](https://www.codacy.com?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=se-passau/VaRA-Tool-Suite&amp;utm_campaign=Badge_Grade) [![codecov](https://codecov.io/gh/se-passau/VaRA-Tool-Suite/branch/vara-dev/graph/badge.svg)](https://codecov.io/gh/se-passau/VaRA-Tool-Suite)

| branch | status |
| :---- | :---: |
| vara | [![Build Status](https://travis-ci.org/se-passau/VaRA-Tool-Suite.svg?branch=vara)](https://travis-ci.org/se-passau/VaRA-Tool-Suite) |
| vara-dev| [![Build Status](https://travis-ci.org/se-passau/VaRA-Tool-Suite.svg?branch=vara-dev)](https://travis-ci.org/se-passau/VaRA-Tool-Suite) |

## Setup Tool Suite

### Install dependencies
To use the VaRA Tool Suite, make sure you have the necessary packages installed.
For ubuntu, you can use the following command to install them (your system has to
have at least `python3.6`):

```bash
sudo apt install python3-dev python3-tk python3-psutil psutils ninja-build python3-pip libpapi-dev
sudo apt install python3-venv # If you want to install VaRA-TS in a python virtualenv
```

### Install VaRA-TS

#### Install to python user-directory (easier)

To install VaRA-TS into the user directory use the following command.
The same command can be used to update an existing installation (if necessary).

```bash
# cd to VaRA-TS directory
python3 -m pip install --user --upgrade -e .

# developers also need to execute the next command
# (if you want to contribute to VaRA/VaRA-TS):
python3 -m pip install -r requirements.txt
```
This initializes `VaRA-TS` and installs the `vara-graphview` tool to visualize VaRA results.

#### Install to python virtualenv (advanced)

```bash
# create virtualenv
python3 -m venv /where/you/want/your/virtualenv/to/live

# activate virtualenv
source /path/to/virtualenv/bin/activate

# cd to VaRA-TS directory
python3 -m pip install --upgrade -e .

# developers also need to execute the next command
# (if you want to contribute to VaRA/VaRA-TS):
python3 -m pip install -r requirements.txt
```

The virtualenv method has the advantage that it does not mess with your local python user
directory. With this method you have to execute the `source` command every time before
you can execute the `vara-graphview` program.

### Install VaRA
Everything around VaRA can be setup automatically with either `vara-buildsetup` or by using the GUI Buildsetup, included in most GUI tools. The following example shows how to setup VaRA via command line.

```bash
    mkdir $VARA_ROOT_FOLDER
    cd $VARA_ROOT_FOLDER
    vara-buildsetup -i
    vara-buildsetup -b
```

Updating VaRA to a new version can also be done with `vara-buildsetup`.
```bash
    vara-buildsetup -u
    vara-buildsetup -b
```

To upgrade VaRA to a new release, for example, `release_70`, use:
```bash
    vara-buildsetup -u --version 70
```

### BenchBuild Projects
`VaRA-TS` defines a set of projects that can be analyzed with `benchbuild`.
```
    benchbuild
    └── projects
```

### BenchBuild Experiments
`VaRA-TS` defines a set of projects that can be analyzed with `benchbuild`.
```
    benchbuild
    └── experiments
```

### Running tests
Running all python tests: 
```bash
    python setup.py test
```
Running all test with coverage:
```bash
    python setup.py test --addopts "--cov=varats --cov-report term-missing"
```
