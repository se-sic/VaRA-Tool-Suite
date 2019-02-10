from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from subprocess import check_call

setup(name='VaRA-Tool-Suite',
      version="0.1",
      url='https://github.com/se-passau/VaRA-Tool-Suite',
      packages=find_packages(exclude=["extern", "benchbuild", "icons",
                                      "results", "uicomponents"]),
      install_requires=[
          "PyQt5>=5.10.0",
          "PyYAML>=3.12",
          "seaborn>=0.8.0",
          "matplotlib>=2.2.0",
          "pandas>=0.22.0",
          "benchbuild>=3.4.2",
          "plumbum>=1.6.6",
          "wllvm>=1.1.4",
      ],
      author="Florian Sattler",
      author_email="sattlerf@fim.uni-passau.de",
      entry_points={
          "gui_scripts": [
              'vara-graphview = varats.driver:main_graph_view',
              'vara-buildsetup = varats.driver:build_setup',
              'vara-gen-commitmap = varats.driver:main_gen_commitmap',
          ]
      })
