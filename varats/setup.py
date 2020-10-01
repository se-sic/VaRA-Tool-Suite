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
        "fallback_version": '10.0.3'
    },
    url='https://github.com/se-passau/vara-tool-suite',
    packages=find_namespace_packages(include=['varats.*']),
    namespace_packages=["varats"],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "PyQt5>=5.10.0,<5.14.0",
        "PyQt5-stubs>=5.10.0,<5.14.0",
        "PyYAML>=3.12",
        "seaborn>=0.8.0",
        "matplotlib>=3.1.2",
        "pandas>=0.22.0",
        "benchbuild>=5.3.1",
        "plumbum>=1.6.6",
        "wllvm>=1.1.4",
        "argparse-utils>=1.2.0",
        "pygit2>=0.28.2",
        "pygtrie",
        "pyzmq>=19.0.0",
        "PyGithub>=1.47",
        "packaging>=20.1",
        "requests>=2.23.0",
        "requests_cache>=0.5.2",
        "scikit-learn~=0.23.1",
        "tabulate>=0.8.6",
        "rich>=1.3.1",
        "statsmodels~=0.11.1",
        "varats-core>10.0.2",
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
    python_requires='>=3.6'
)
