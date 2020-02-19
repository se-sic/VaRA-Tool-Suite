from setuptools import setup, find_packages

setup(name='VaRA-Tool-Suite',
      version="9.0.0",
      url='https://github.com/se-passau/VaRA-Tool-Suite',
      packages=find_packages(
          exclude=["extern", "benchbuild", "icons", "results", "uicomponents"]),
      setup_requires=["pytest-runner"],
      tests_require=["pytest", "pytest-cov"],
      install_requires=[
          "PyQt5>=5.10.0,<5.14.0",
          "PyYAML>=3.12",
          "seaborn>=0.8.0",
          "matplotlib>=3.1.2",
          "pandas>=0.22.0",
          "benchbuild>=4.0.1",
          "plumbum>=1.6.6",
          "wllvm>=1.1.4",
          "argparse-utils>=1.2.0",
          "pygit2>=0.28.2",
      ],
      author="Florian Sattler",
      author_email="sattlerf@cs.uni-saarland.de",
      entry_points={
          "gui_scripts": [
              'vara-graphview = varats.driver:main_graph_view',
              'vara-gen-commitmap = varats.driver:main_gen_commitmap',
          ],
          "console_scripts": [
              'vara-buildsetup = varats.driver:build_setup',
              'vara-art = varats.tools.driver_artefacts:main',
              'vara-cs = varats.driver:main_casestudy',
              'vara-develop = varats.driver:main_develop',
              'vara-gen-bbconfig = varats.driver:main_gen_benchbuild_config',
              'vara-plot = varats.driver:main_plot',
              'vd = varats.driver:main_develop',
          ]
      },
      python_requires='>=3.6')
