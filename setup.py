from setuptools import find_packages, setup

setup(
    name='VaRA-Tool-Suite',
    version="10.0.0",
    url='https://github.com/se-passau/VaRA-Tool-Suite',
    packages=find_packages(
        exclude=["extern", "benchbuild", "icons", "results", "uicomponents"]
    ),
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "PyQt5>=5.10.0,<5.14.0",
        "PyQt5-stubs>=5.10.0,<5.14.0",
        "PyYAML>=3.12",
        "seaborn>=0.8.0",
        "matplotlib>=3.1.2",
        "pandas>=0.22.0",
        "benchbuild>=4.1.0,<5.0.0",
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
        "tabulate>=0.8.6",
        "rich>=1.3.1",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    entry_points={
        "gui_scripts": [
            'vara-graphview = varats.tools.driver_graph_view:main',
        ],
        "console_scripts": [
            'vara-art = varats.tools.driver_artefacts:main',
            'vara-buildsetup = varats.tools.driver_build_setup:main',
            'vara-config = varats.tools.driver_config:main',
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
