# VaRA Tool Suite

## Project Status [![Codacy Badge](https://api.codacy.com/project/badge/Grade/a52d7d5380a24733b2540e0f6d8a6112)](https://www.codacy.com?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=se-passau/VaRA-Tool-Suite&amp;utm_campaign=Badge_Grade) [![codecov](https://codecov.io/gh/se-passau/VaRA-Tool-Suite/branch/vara-dev/graph/badge.svg)](https://codecov.io/gh/se-passau/VaRA-Tool-Suite) [![Documentation Status](https://readthedocs.org/projects/vara-tool-suite/badge/?version=vara-dev)](https://vara-tool-suite.readthedocs.io/en/vara-dev/?badge=vara-dev)

| branch  | status                                                                                                                                   |
| :----   | :---:                                                                                                                                   |
| vara    | [![Build Status](https://travis-ci.org/se-passau/VaRA-Tool-Suite.svg?branch=vara)](https://travis-ci.org/se-passau/VaRA-Tool-Suite) |
| vara-dev| [![Build Status](https://travis-ci.org/se-passau/VaRA-Tool-Suite.svg?branch=vara-dev)](https://travis-ci.org/se-passau/VaRA-Tool-Suite) |

## Using VaRA with VaRA-TS
VaRA is a variability-aware framework to analyze interactions between code regions that convey a semantic meaning for the researcher, e.g., `CommitRegions` represent blocks of code that belongs to the same commit.
Our tool suite allows the researcher to automatically run analyses provided by VaRA on different software projects.
For this, we provides different preconfigured experiments and projects.
Experiments abstract the actions that should be taken when analyzing a project, e.g., build, analyze, generate result graph.
Projects describe how a software project should be configured and build, e.g., `gzip` provides all necessary information to checkout, configure, and compile the project.

## Setup Tool Suite

### Install dependencies
To use the VaRA Tool Suite, make sure you have the necessary packages installed.
For ubuntu, you can use the following command to install them (your system has to
have at least `python3.6`):

```bash
sudo apt install python3-dev python3-tk python3-psutil psutils ninja-build python3-pip autoconf cmake ruby curl time libyaml-dev
sudo apt install python3-venv # If you want to install VaRA-TS in a python virtualenv
```

Additional packages are required to build VaRA from source.
```bash
sudo apt install libsqlite3-dev libcurl4-openssl-dev libboost-all-dev libpapi-dev googletest
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

## Running experiments and analyzing projects
VaRA-TS provides different preconfigured experiments and projects.
In order to execute an experiment on a project we use BenchBuild, an empirical-research toolkit.

### Setup: Configuring BenchBuild
First, we need to generate a folder with a configuration file for BenchBuild in the vara root directory, this is done with:
```console
vara-gen-bbconfig
```

### Running BenchBuild experiments
Second, we change into the benchbuild folder and run an experiment that generates `CommitReports` for provided projects, in this case we use `gzip`.
```console
cd $VARA_ROOT/benchbuild
benchbuild -vv run -E GenerateCommitReport gzip
```
The generated result files are place in the `vara/results/$PROJECT_NAME` folder and can be further visualized with VaRA-TS graph generators.

### Creating a CaseStudy
If one wants to analyze a particular set of revisions or wants to reevaluate the same revision over and over again, we can fix the analyzed revisions by creating a `CaseStudy`. First, create a folder, where your config should be saved. Then, create a case study that fixes the revision to be analyzed.
In order to ease the creation of case studies VaRA-TS offers different sampling methods to choose revisions from the projects history based on a probability distribution.

For example, we can generate a new case study for `gzip`, drawing 10 revision from the projects history based on a half-normal distribution, with:
```console
vara-cs gen PATH_TO_PAPER_CONF_DIR/ half_norm PATH_TO_REPO/ --num-rev 10
```

Created case studies should be grouped into folders, e.g., a set of case studies used for a paper.
This allows the tool suite to tell BenchBuild which revisions should be analyzed to evaluate a set of case studies for a paper. For example, a setup could look like:
```console
paper_configs
    ├── ase-17
    │       ├── gzip_0.case_study
    │       ├── gzip_1.case_study
    │       └── git_0.case_study
    └── icse-18
            ├── gzip_0.case_study
            └── git_0.case_study
```
In this example, we got two paper configs, one for `ase-17` another for `icse-18`. We see different case studies for `gzip` and `git`, notice here that we can create multiple case studies for one project. If we now want to evaluate our set for `icse-18` we set the paper-config folder to the root of our config tree and select the `icse-18` folder as our current config.
```yaml
paper_config:
    current_config:
        value: icse-18
    folder:
        value: /home/foo/vara/paper_configs/
```
Next, we can run our experiment with BenchBuild as usual. During experiment execution BenchBuild will load our config and only evaluate the needed revisions.

The current status of a case study can be visualized with `vara-cs status`:
```console
> vara-cs status -s
CS: gzip_0: (0/5) processed
CS: gzip_1: (2/5) processed
CS: gzip_2: (5/5) processed
CS: libvpx_0: (0/5) processed
```
### Extending a CaseStudy
Case studies group together revisions but sometimes these groups need to be changed or extended, e.g., when we want so sample a few more revisions to gather data for a specific revision range.
To simplify that, our tool suite provides `vara-cs ext`, a tool for extending and changing case studies.

For example:
```console
vara-cs ext paper_configs/ase-17/gzip_0.case_study distrib_add gzip/ --distribution uniform --num-rev 5
```
will add 5 new revision, sampled uniformly, to the case study.

In more detail, case studies have different stages that are separated from each other.
This allows us to for example extend a case study with an specific revision without changing the initial set of revisions, e.g., stage 0.

For example:
```console
vara-cs ext paper_configs/ase-17/gzip_0.case_study simple_add gzip/ --extra-revs 0dd8313ea7bce --merge-stage 3
```
will add revision `0dd8313ea7bce` to the stage 3 of the gzip case study, allowing us to analyze it and draw different plots, e.g., one containing only stage 0 data and another with all stages included. 

## VaRA developer tools
VaRA-TS provides different tools to ease VaRA development.

### vara-develop
`vara-develop`, short `vd`, is a helper to interact with the different VaRA project repositories when working on VaRA.
The tool provides commands for showing `git status`, creating `new-branch` or `checkout` existing branches.
Furthermore, commands to `pull`/`push` the current branches and to show currently developed feature branches `f-branches`.
It can be used on a set of projects simultaneously.
A command like:
```console
> vd new-branch f-FooBar vara clang llvm
```
will create the branch `f-FooBar` on all three repositories.

Showing the current status of the listed projects can be done with:
```console
> vd status clang vara
################################################################################
# Project: clang                                                               #
################################################################################
On branch vara-80-dev
Your branch is up to date with 'origin/vara-80-dev'.

nothing to commit, working tree clean

################################################################################
# Project: VaRA                                                                #
################################################################################
On branch f-InstrumentationVerifier
Your branch is up to date with 'origin/f-InstrumentationVerifier'.

nothing to commit, working tree clean
```

The `checkout` tool helps you to checkout the same branch on different projects, if one exists.
Furthermore, it can easily switch all projects to `vara-dev` or `vara` by just typing:
```console
vd checkout vara-dev
```

To get a full overview of the tool use `vd -h` and `vd {sub_command} -h`.

## Extending the tool suite
VaRA-TS allows the user to extend it with different projects, experiments, and data representations.

### BenchBuild Projects
`VaRA-TS` defines a set of projects that can be analyzed with `benchbuild`.
```console
    benchbuild
    └── projects
```

### BenchBuild Experiments
`VaRA-TS` defines a set of projects that can be analyzed with `benchbuild`.
```console
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
