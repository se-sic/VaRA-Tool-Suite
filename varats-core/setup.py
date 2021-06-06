"""Setup config for the varats-core namespace package."""
from setuptools import find_namespace_packages, setup

setup(
    name='varats-core',
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
        "benchbuild>=6.0.1",
        "plumbum>=1.6.6",
        "PyGithub>=1.47",
        "PyDriller>=2.0",
        "tabulate>=0.8.6",
        "requests>=2.23.0",
        "packaging>=20.1",
        "requests_cache>=0.5.2",
        "pygit2>=0.28.2",
        "pytz>=2021.1",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    python_requires='>=3.7'
)
