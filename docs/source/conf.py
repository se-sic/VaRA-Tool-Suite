# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import logging
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

import benchbuild.utils
# -- Project information -----------------------------------------------------
from pkg_resources import DistributionNotFound, get_distribution

sys.path.insert(0, os.path.abspath('../../'))

# pylint: skip-file

try:
    __version__ = get_distribution("varats").version
except DistributionNotFound:
    pass

project = 'VaRA'
copyright = '2020, Florian Sattler'
author = 'Florian Sattler'

# The full version, including alpha/beta/rc tags
release = __version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.autosectionlabel',
    'sphinxcontrib.programoutput',
    'sphinx_autodoc_typehints',
]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'haiku'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

pygments_style = 'sphinx'

autodoc_member_order = "bysource"
add_function_parentheses = True
add_module_names = True

# Import pandas without the type checking flag to avoid import errors.
# The exact reason for these errors is unknown but might be related to
# incompatible cython versions (https://github.com/cython/cython/issues/1953)
import pandas  # isort:skip
import numpy.typing as npt  # isort:skip

# The autodocs typehints plugin does not resolve circular imports caused by type
# annotations, so we have to manually break the circles.
import rich.console  # isort:skip
import cryptography.hazmat.backends  # isort:skip
import click  # isort:skip
import git  # isort:skip

import typing as tp  # isort:skip

tp.TYPE_CHECKING = True
import varats.mapping.commit_map  # isort:skip
import varats.plot.plot  # isort:skip
import varats.table.table  # isort:skip
import varats.containers.containers  # isort:skip

tp.TYPE_CHECKING = False

# set the type checking flag so all types can be resolved in the docs
set_type_checking_flag = True

# -- Prevent import warnings -------------------------------------------------

benchbuild.utils.LOG.setLevel(logging.ERROR)

# -- Generate files ----------------------------------------------------------

from pathlib import Path

from varats.projects.discover_projects import initialize_projects
from varats.ts_utils.doc_util import (
    generate_project_overview_table_file,
    generate_projects_autoclass_files,
    generate_vara_install_requirements,
)

initialize_projects()

generate_project_overview_table_file(
    Path("vara-ts-api/ProjectOverviewTable.inc")
)
generate_projects_autoclass_files(Path("vara-ts-api"))
generate_vara_install_requirements(Path("vara-ts"))
