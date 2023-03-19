"""Setup config for the varats-core namespace package."""
from setuptools import find_namespace_packages, setup

setup(
    name='varats-core',
    version='13.0.3',
    url='https://github.com/se-sic/vara-tool-suite',
    packages=find_namespace_packages(include=['varats.*']),
    namespace_packages=["varats"],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "benchbuild>=6.6.4",
        "ijson>=3.1.4",
        "plumbum>=1.6",
        "PyGithub>=1.58",
        "PyDriller>=2.4.1",
        "requests>=2.28.2",
        "packaging>=20.1",
        "pygit2>=1.10",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    python_requires='>=3.9'
)
