from setuptools import setup, find_packages

setup(
    name='VaRA-Tool-Suite',
    version="8.0.0",
    url='https://github.com/se-passau/VaRA-Tool-Suite',
    packages=find_packages(
        exclude=["extern", "benchbuild", "icons", "results", "uicomponents"]),
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "PyQt5>=5.10.0",
        "PyYAML>=3.12",
        "seaborn>=0.8.0",
        "matplotlib>=2.2.0",
        "pandas>=0.22.0",
        "benchbuild>=3.5.0",
        "plumbum>=1.6.6",
        "wllvm>=1.1.4",
        "argparse-utils>=1.2.0",
    ],
    author="Florian Sattler",
    author_email="sattlerf@fim.uni-passau.de",
    entry_points={
        "gui_scripts": [
            'vara-graphview = varats.driver:main_graph_view',
            'vara-buildsetup = varats.driver:build_setup',
            'vara-gen-commitmap = varats.driver:main_gen_commitmap',
        ],
        "console_scripts": [
            'vara-develop = varats.driver:main_develop',
            'vd = varats.driver:main_develop',
            'vara-gen-graph = varats.driver:main_gen_graph',
            'vara-gen-bbconfig = varats.driver:main_gen_benchbuild_config',
            'vara-cs = varats.driver:main_casestudy',
        ]
    },
    python_requires='>=3.6')
