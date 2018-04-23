from setuptools import setup, find_packages

setup(name='VaRA-Tool-Suite',
      version="0.1",
      url='https://github.com/se-passau/VaRA-Tool-Suite',
      packages=find_packages(exclude=["extern", "benchbuild", "icons",
                                      "results", "uicomponents"]),
      install_requires=[
          "PyQt5>=5.10.0",
      ],
      author="Florian Sattler",
      author_email="sattlerf@fim.uni-passau.de",
      entry_points={
          "gui_scripts": [
              'vara-graphview = varats.driver:main'
          ]
      })
