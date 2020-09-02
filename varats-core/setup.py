"""Setup config for the varats-core namespace package."""
from setuptools import find_namespace_packages, setup

setup(
    name='varats-core',
    use_scm_version={
        'root': '..',
        "relative_to": __file__,
        "fallback_version": '10.0.0'
    },
    url='https://github.com/se-passau/vara-tool-suite',
    packages=find_namespace_packages(include=['varats.*']),
    namespace_packages=["varats"],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "pytest-cov"],
    install_requires=[
        "benchbuild>=5.2",
    ],
    author="Florian Sattler",
    author_email="sattlerf@cs.uni-saarland.de",
    python_requires='>=3.6'
)
