"""Setup config for the varats namespace package."""
import os

from setuptools import find_namespace_packages, setup

base_dir = os.path.dirname(__file__)

with open(base_dir + '/README.md') as f:
    long_description = f.read()

setup(
    name='varats',
    version='13.0.5',
    url='https://github.com/se-sic/vara-tool-suite',
    packages=find_namespace_packages(include=['varats.*']),
    namespace_packages=["varats"],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "benchbuild>=6.8",
        "click>=8.1.3",
        "distro>=1.5.0",
        "graphviz>=0.14.2",
        "Jinja2>=3.1.2",
        "kaleido>=0.2.1",
        "matplotlib>=3.8.2",
        "networkx>=3.0",
        "numpy>=1.24.2",
        "packaging>=20.1",
        "pandas>=1.5.3",
        "plotly>=5.13.1",
        "plumbum>=1.6",
        "pygit2>=1.10",
        "PyGithub>=1.47",
        "pygraphviz>=1.7",
        "pygtrie>=2.3",
        "pylatex>=1.4.1",
        "PyQt5>=5.10.0",
        "PyQt5-stubs>=5.10.0",
        "PyYAML>=6.0",
        "rich>=12.6",
        "scikit-learn>=1.2.2",
        "seaborn>=0.13.0",
        "tabulate>=0.9",
        "varats-core>=13.0.5",
        "wllvm>=1.3.1",
        "cliffs-delta>=1.0.0",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    license="BSD 2-Clause",
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        "gui_scripts": [
            'vara-graphview = varats.tools.driver_graph_view:main',
            'vara-buildsetup-gui = varats.tools.driver_build_setup_gui:main',
        ],
        "console_scripts": [
            'vara-art = varats.tools.driver_artefacts:main',
            'vara-buildsetup = varats.tools.driver_build_setup:main',
            'vara-config = varats.tools.driver_config:main',
            'vara-container = varats.tools.driver_container:main',
            'vara-cs = varats.tools.driver_casestudy:main',
            'vara-cs-gui = varats.tools.driver_casestudy_gui:main',
            'vara-develop = varats.tools.driver_develop:main',
            'vd = varats.tools.driver_develop:main',
            'vara-gen-bbconfig = '
            'varats.tools.driver_gen_benchbuild_config:main',
            'vara-pc = varats.tools.driver_paper_config:main',
            'vara-plot = varats.tools.driver_plot:main',
            'vara-run = varats.tools.driver_run:main',
            'vara-table = varats.tools.driver_table:main',
            'vara-cve = varats.tools.driver_cve:main',
        ]
    },
    python_requires='>=3.9'
)
