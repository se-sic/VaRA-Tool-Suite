"""Setup config for the varats namespace package."""
import os

from setuptools import find_namespace_packages, setup

base_dir = os.path.dirname(__file__)

with open(base_dir + '/README.md') as f:
    long_description = f.read()

setup(
    name='varats',
    use_scm_version={
        'root': '..',
        "relative_to": __file__,
        "fallback_version": '11.0.0'
    },
    url='https://github.com/se-passau/vara-tool-suite',
    packages=find_namespace_packages(include=['varats.*']),
    namespace_packages=["varats"],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "argparse-utils>=1.2.0",
        "benchbuild>=6.2.0",
        "click>=8.0.1",
        "graphviz>=0.14.2",
        "Jinja2>=3.0.1",
        "kaleido>=0.2.1",
        "matplotlib>=3.1.2",
        "numpy>=1.20",
        "packaging>=20.1",
        "pandas>=0.22.0",
        "plotly>=4.14.1",
        "plumbum>=1.6.6",
        "pygit2>=0.28.2",
        "PyGithub>=1.47",
        "pygtrie",
        "pylatex>=1.4.1",
        "PyQt5>=5.10.0",
        "PyQt5-stubs>=5.10.0",
        "PyYAML>=5.1",
        "pyzmq>=19.0.0",
        "requests>=2.24.0",
        "requests_cache>=0.5.2",
        "rich>=1.3.1",
        "scikit-learn~=0.23.1",
        "seaborn>=0.8.0",
        "statsmodels~=0.11.1",
        "tabulate>=0.8.6",
        "varats-core>=11.0.0",
        "wllvm>=1.1.4",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    license="BSD 2-Clause",
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        "gui_scripts": [
            'vara-graphview = varats.tools.driver_graph_view:main',
        ],
        "console_scripts": [
            'vara-art = varats.tools.driver_artefacts:main',
            'vara-buildsetup = varats.tools.driver_build_setup:main',
            'vara-config = varats.tools.driver_config:main',
            'vara-container = varats.tools.driver_container:main',
            'vara-cs = varats.tools.driver_casestudy:main',
            'vara-develop = varats.tools.driver_develop:main',
            'vd = varats.tools.driver_develop:main',
            'vara-gen-bbconfig = '
            'varats.tools.driver_gen_benchbuild_config:main',
            'vara-gen-commitmap = varats.tools.driver_gen_commitmap:main',
            'vara-pc = varats.tools.driver_paper_config:main',
            'vara-plot = varats.tools.driver_plot:main',
            'vara-table = varats.tools.driver_table:main',
            'vara-cve = varats.tools.driver_cve:main',
        ]
    },
    python_requires='>=3.7'
)
